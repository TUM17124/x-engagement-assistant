"""Official asynchronous text-to-video adapters, separate from text AI and social posting."""
import asyncio, hashlib, json, re, time, uuid
from abc import ABC, abstractmethod
from urllib.parse import urlsplit, urljoin, quote
import httpx
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from . import database as db, media
from .ai_connections import policy
from .ai_registry import CATALOG
from .ai_adapters import request
from .errors import check_response, ServiceError
from .secrets import store

VIDEO_META={
 "gemini":{"name":"Google Gemini / Veo", "docs":"https://ai.google.dev/gemini-api/docs/veo","note":"Veo long-running generation API. Gemini Omni uses a different API and is not supported by this adapter."},
 "grok":{"name":"xAI / Grok video", "docs":"https://docs.x.ai/developers/model-capabilities/video/generation","note":"Official asynchronous video generation. Temporary outputs should be saved promptly."}
}
LOCK=asyncio.Lock()
class VideoConfig(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    provider:str=""
    model:str=Field(default="",max_length=200)
    daily_limit:int=Field(default=3,ge=1,le=20)
class VideoSetup(VideoConfig):
    api_key:SecretStr|None=Field(default=None,max_length=8192)
class VideoRequest(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    prompt:str=Field(min_length=5,max_length=4000)
    confirmed:bool=False
    request_id:str=Field(min_length=16,max_length=64,pattern=r"^[a-zA-Z0-9-]+$")
class VideoProvider(ABC):
    def __init__(self,key):self.key=key
    @abstractmethod
    async def models(self):...
    @abstractmethod
    async def start(self,model,prompt):...
    @abstractmethod
    async def status(self,ident):...
    async def call(self,method,path,**kwargs):
        async with httpx.AsyncClient(timeout=60,follow_redirects=False) as client:
            r=await request(client,method,self.base+path,self.name,headers=self.headers(),**kwargs)
        try:return r.json()
        except ValueError:raise ValueError("Video provider returned an unreadable response.") from None
class GeminiVideoProvider(VideoProvider):
    base="https://generativelanguage.googleapis.com/v1beta";name="Gemini Video"
    def headers(self):return {"x-goog-api-key":self.key}
    async def models(self):
        out=[];params={}
        for _ in range(20):
            data=await self.call("GET","/models",params=params)
            out.extend({"id":m["name"].removeprefix("models/"),"name":m.get("displayName",m["name"])} for m in data.get("models",[]) if "predictLongRunning" in m.get("supportedGenerationMethods",[]))
            if not data.get("nextPageToken"):break
            params={"pageToken":data["nextPageToken"]}
        return out
    async def start(self,model,prompt):
        d=await self.call("POST","/models/"+quote(model,safe="")+":predictLongRunning",json={"instances":[{"prompt":prompt}]})
        ident=d.get("name","")
        if not re.fullmatch(r"(?:models/[a-zA-Z0-9_.-]+/)?operations/[a-zA-Z0-9_.-]+",ident):raise ValueError("Video request was sent but no valid operation ID was returned. Check the provider before repeating.")
        return ident
    async def status(self,ident):
        if not re.fullmatch(r"(?:models/[a-zA-Z0-9_.-]+/)?operations/[a-zA-Z0-9_.-]+",ident):raise ValueError("Invalid video operation.")
        d=await self.call("GET","/"+ident)
        if d.get("error"):return "failed",""
        if not d.get("done"):return "processing",""
        samples=(d.get("response") or {}).get("generateVideoResponse",{}).get("generatedSamples") or []
        return ("ready",samples[0]["video"]["uri"]) if samples else ("failed","")
class XAIVideoProvider(VideoProvider):
    base="https://api.x.ai/v1";name="xAI Video"
    def headers(self):return {"Authorization":"Bearer "+self.key}
    async def models(self):
        d=await self.call("GET","/video-generation-models")
        return [{"id":m["id"],"name":m["id"]} for m in d["models"]]
    async def start(self,model,prompt):
        d=await self.call("POST","/videos/generations",json={"model":model,"prompt":prompt,"duration":5,"aspect_ratio":"16:9","resolution":"720p"})
        ident=d.get("request_id","")
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,200}",ident):raise ValueError("Video request was sent but no valid request ID was returned. Check the provider before repeating.")
        return ident
    async def status(self,ident):
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,200}",ident):raise ValueError("Invalid video request ID.")
        d=await self.call("GET","/videos/"+ident);state=d.get("status")
        if state=="done":
            video=d.get("video") or {}
            return ("ready",video.get("url","")) if video.get("respect_moderation") is not False else ("failed","")
        if state in {"failed","expired"}:return state,""
        if state in {"pending","processing","queued","in_progress"}:return "processing",""
        raise ValueError("Video provider returned an unknown job state. No new generation was submitted.")
ADAPTERS={"gemini":GeminiVideoProvider,"grok":XAIVideoProvider}
def build(kind,key=None):
    if kind not in ADAPTERS:raise ValueError("Choose a supported video provider.")
    key=key if key is not None else store.get("video_api_key_"+kind)
    if not key:raise ValueError("Add a video API key in Settings > Video Generation.")
    return ADAPTERS[kind](key)
def configuration():return VideoConfig.model_validate(db.get_setting("video_configuration",{}))
def enabled():
    if policy().local_only:raise ValueError("Local AI Only blocks cloud video generation and downloads.")
def job(ident):
    row=db.one("SELECT * FROM video_jobs WHERE id=?",(ident,))
    if not row:raise ValueError("Video job not found.")
    return row
def public_job(row):return {k:v for k,v in row.items() if k not in {"remote_id","fingerprint"}}
async def generate(data):
    enabled()
    if not data.confirmed:raise ValueError("Confirm that this video request may incur provider charges.")
    cfg=configuration();adapter=build(cfg.provider)
    if not cfg.model:raise ValueError("Choose a video model in Settings.")
    async with LOCK:
        fingerprint=hashlib.sha256((cfg.provider+cfg.model+data.prompt).encode()).hexdigest()
        prior=db.one("SELECT * FROM video_jobs WHERE id=? OR fingerprint=? ORDER BY created_at DESC LIMIT 1",(data.request_id,fingerprint))
        if prior:return {"job":public_job(prior),"message":"An existing request was found. Check its status before generating another clip."}
        used=db.one("SELECT COUNT(*) n FROM video_jobs WHERE substr(created_at,1,10)=?",(db.now()[:10],))["n"]
        if used>=cfg.daily_limit:raise ValueError("Daily video generation limit reached. Review your existing jobs or change the video limit in Settings.")
        db.execute("INSERT INTO video_jobs(id,provider,model,prompt,fingerprint,status,created_at) VALUES(?,?,?,?,?,'uncertain',?)",(data.request_id,cfg.provider,cfg.model,data.prompt,fingerprint,db.now()))
        try:
            remote=await adapter.start(cfg.model,data.prompt)
            db.execute("UPDATE video_jobs SET remote_id=?,status='processing',next_poll=? WHERE id=?",(remote,time.time()+15,data.request_id))
        except (ServiceError,ValueError):
            db.execute("UPDATE video_jobs SET error=? WHERE id=?",("Submission could not be confirmed. Check the provider dashboard; this request will never be retried automatically.",data.request_id));raise
        return {"job":public_job(job(data.request_id)),"message":"Video generation started. Check status here; nothing is posted to social media."}
async def poll(ident):
    enabled()
    async with LOCK:
        row=job(ident)
        if row["status"]!="processing" or row["next_poll"]>time.time():return public_job(row)
        db.execute("UPDATE video_jobs SET next_poll=? WHERE id=?",(time.time()+30,ident))
        try:state,url=await build(row["provider"]).status(row["remote_id"])
        except ServiceError as e:
            db.execute("UPDATE video_jobs SET next_poll=?,error=? WHERE id=?",(time.time()+max(30,e.retry_after),str(e),ident));raise
        if state=="ready":
            validate_download(url,row["provider"])
            store.set("video_output_"+ident,url)  # Signed output links stay out of renderer and plaintext SQLite.
        error="Provider failed, expired or filtered this generation. Check its dashboard; nothing was posted." if state in {"failed","expired"} else ""
        db.execute("UPDATE video_jobs SET status=?,error=? WHERE id=?",(state,error,ident))
        return public_job(job(ident))
def validate_download(url,kind):
    try:
        u=urlsplit(url);host=u.hostname or ""
        permitted=(host=="vidgen.x.ai") if kind=="grok" else (host=="generativelanguage.googleapis.com" or host=="storage.googleapis.com" or host.endswith(".googleusercontent.com"))
        if u.scheme!="https" or not permitted or u.username or u.password or u.port not in {None,443} or "\\" in url:raise ValueError()
        return url
    except ValueError:raise ValueError("Video output uses an unrecognized download host. Check the official provider dashboard; credentials were not forwarded.") from None
async def download(ident):
    enabled()
    async with LOCK:
        row=job(ident)
        if row["media_id"] and db.one("SELECT id FROM media WHERE id=?",(row["media_id"],)):return {"media_id":row["media_id"],"message":"Video is already in Media Library."}
        if row["status"]!="ready":raise ValueError("Check status until the video is ready before saving it.")
        url=store.get("video_output_"+ident);adapter=build(row["provider"]);payload=bytearray()
        async with httpx.AsyncClient(timeout=120,follow_redirects=False) as client:
            for _ in range(4):
                validate_download(url,row["provider"])
                headers=adapter.headers() if urlsplit(url).hostname=="generativelanguage.googleapis.com" else {}
                async with client.stream("GET",url,headers=headers) as response:
                    if 300<=response.status_code<400:
                        url=urljoin(url,response.headers.get("location",""));continue
                    check_response(response,"Video download")
                    async for chunk in response.aiter_bytes():
                        payload.extend(chunk)
                        if len(payload)>50*1024*1024:raise ValueError("This video exceeds the 50 MB media limit. Download it from your provider dashboard.")
                    break
            else:raise ValueError("Too many video download redirects.")
        if len(payload)<16 or payload[4:8]!=b"ftyp":raise ValueError("Provider output is not a supported MP4 file.")
        saved=media.add(bytes(payload),"generated-video-"+ident[:8]+".mp4")
        db.execute("UPDATE video_jobs SET media_id=?,status='saved' WHERE id=?",(saved["id"],ident));store.delete("video_output_"+ident)
        return {"media_id":saved["id"],"message":"Video saved locally in Media Library. Review and attach it in Create; nothing was published."}
router=APIRouter(prefix="/api/video")
@router.get("/settings")
def get_settings():
    return {"config":configuration().model_dump(),"providers":[{"id":k,**v,"key_mask":store.masked("video_api_key_"+k),"key_url":CATALOG[k]["key_url"],"pricing_url":CATALOG[k]["pricing_url"],"privacy_url":CATALOG[k]["privacy_url"]} for k,v in VIDEO_META.items()]}
@router.post("/test")
async def test(data:VideoSetup):
    key=data.api_key.get_secret_value().strip() if data.api_key is not None else None
    models=await build(data.provider,key).models()
    return {"models":models,"message":"Video model discovery succeeded. Generation also requires provider credits and permissions."}
@router.put("/settings")
async def save(data:VideoSetup):
    result=await test(data)
    if data.model not in {m["id"] for m in result["models"]}:raise ValueError("Select an available video model after Test connection.")
    if data.api_key is not None:store.set("video_api_key_"+data.provider,data.api_key.get_secret_value().strip())
    db.set_setting("video_configuration",data.model_dump(exclude={"api_key"}));return {"saved":True,"message":"Video provider saved"}
@router.delete("/keys/{kind}")
def delete_key(kind:str):
    if kind not in ADAPTERS:raise ValueError("Unknown video provider.")
    store.delete("video_api_key_"+kind);return {"deleted":True}
@router.get("/jobs")
def jobs():return [public_job(r) for r in db.rows("SELECT * FROM video_jobs ORDER BY created_at DESC LIMIT 100")]
@router.post("/jobs")
async def start(data:VideoRequest):return await generate(data)
@router.post("/jobs/{ident}/status")
async def status(ident:str):return await poll(ident)
@router.post("/jobs/{ident}/save")
async def save_media(ident:str):return await download(ident)
