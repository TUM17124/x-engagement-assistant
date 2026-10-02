"""Separate image generation and vision assistance, invoked only by explicit UI actions."""
from abc import ABC,abstractmethod
import base64
import io
from urllib.parse import urlsplit,quote
import httpx
from PIL import Image,ImageOps
from . import preferences as prefs,media
from .secrets import store
from .errors import request

class ImageProvider(ABC):
    @abstractmethod
    async def generate(self,prompt):...

class CompatibleImageProvider(ImageProvider):
    async def generate(self,prompt):
        cfg=prefs.get("image_provider")
        endpoint=cfg.get("endpoint","").rstrip("/")
        url=urlsplit(endpoint)
        if (url.scheme!="https" and not(url.scheme=="http" and url.hostname in {"localhost","127.0.0.1"})) or url.username or url.password or url.query:
            raise ValueError("Configure an HTTPS image endpoint, or a local HTTP endpoint, in AI Provider.")
        key=store.get("image_api_key")
        async with httpx.AsyncClient(timeout=120) as client:
            r=await request(client,"POST",endpoint+"/images/generations","Image AI",headers={"Authorization":"Bearer "+key},
                json={"model":cfg.get("model",""),"prompt":prompt,"n":1,"size":"1024x1024","response_format":"b64_json"})
        try:
            data=base64.b64decode(r.json()["data"][0]["b64_json"],validate=True)
        except (KeyError,IndexError,ValueError,TypeError):
            raise ValueError("This adapter requires a base64 image response. Remote download URLs are not fetched.") from None
        return media.add(data,"generated.png")

async def describe(id,instruction):
    if prefs.get("ai_provider")=="chatgpt":
        raise ValueError("The ChatGPT plan adapter currently supports text. Select a vision-capable Gemini, OpenAI, compatible, or Ollama model for image assistance.")
    row=__import__("app.database",fromlist=["one"]).one("SELECT * FROM media WHERE id=?",(id,))
    if not row or not row["mime"].startswith("image/"):raise ValueError("Choose an image for visual assistance.")
    with Image.open(media.media_path(id)) as source:
        image=ImageOps.exif_transpose(source).convert("RGB");image.thumbnail((1024,1024))
        out=io.BytesIO();image.save(out,"JPEG",quality=85)
    encoded=base64.b64encode(out.getvalue()).decode()
    kind=prefs.get("ai_provider");model=prefs.get("ai_model");key=store.get("ai_api_key_"+kind)
    prompt="Describe only visible details. Do not identify people or invent product claims. "+instruction[:1000]
    async with httpx.AsyncClient(timeout=90) as client:
        if kind=="gemini":
            r=await request(client,"POST","https://generativelanguage.googleapis.com/v1beta/models/"+quote(model,safe="")+":generateContent","AI",
                headers={"x-goog-api-key":key},json={"contents":[{"parts":[{"text":prompt},{"inlineData":{"mimeType":"image/jpeg","data":encoded}}]}]})
            text="".join(x.get("text","") for x in r.json().get("candidates",[{}])[0].get("content",{}).get("parts",[]) if not x.get("thought"))
        elif kind=="ollama":
            r=await request(client,"POST",(prefs.get("ai_base_url") or "http://127.0.0.1:11434").rstrip("/")+"/api/chat","AI",
                json={"model":model,"stream":False,"messages":[{"role":"user","content":prompt,"images":[encoded]}]})
            text=r.json().get("message",{}).get("content","")
        else:
            endpoint="https://api.openai.com/v1" if kind=="openai" else prefs.get("ai_base_url")
            r=await request(client,"POST",endpoint.rstrip("/")+"/chat/completions","AI",headers={"Authorization":"Bearer "+key},
                json={"model":model,"messages":[{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+encoded}}]}],"max_tokens":700})
            text=r.json().get("choices",[{}])[0].get("message",{}).get("content","")
    if not text:raise ValueError("No visual description returned. Select a model with image support.")
    return text
