"""Validated non-secret settings, migration, routing and privacy policy shared by all AI features."""
import json, time, hashlib
from datetime import datetime,timezone
from urllib.parse import urlsplit
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator
from . import database as db, preferences as prefs
from .secrets import store
from .ai_registry import CATALOG, validate_url, is_loopback

class Connection(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    name: str = Field(default="",max_length=100)
    model: str = Field(default="",max_length=200)
    base_url: str = Field(default="",max_length=1000)
    enabled: bool = True
    local: bool = False
    manual_model: bool = False

class ConnectionInput(Connection):
    api_key: SecretStr | None = Field(default=None,max_length=8192)

class Policy(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    local_only: bool = False
    fallback_enabled: bool = False
    fallback: str = ""
    overrides: dict[str,str] = Field(default_factory=dict)
    feature_models: dict[str,str] = Field(default_factory=dict)
    send_voice: bool = True
    send_profile: bool = True
    send_product: bool = True
    send_conversation: bool = True
    usage_log: bool = True
    prompt_history: bool = False
    @model_validator(mode="after")
    def validate_routes(self):
        features={"replies","posts","trends","summaries","vision","research","planner","terminal"}
        if self.fallback and self.fallback not in CATALOG:raise ValueError("Unknown fallback provider.")
        if set(self.overrides)-features or set(self.feature_models)-features:raise ValueError("Unknown AI feature.")
        if any(v not in CATALOG for v in self.overrides.values()):raise ValueError("Unknown feature provider.")
        if any(len(v)>200 for v in self.feature_models.values()):raise ValueError("Model ID is too long.")
        if self.local_only:self.fallback_enabled=False
        return self

def policy():return Policy.model_validate(db.get_setting("ai_policy",{}))
def config(kind):
    row=db.one("SELECT config FROM ai_connections WHERE id=?",(kind,))
    return json.loads(row["config"]) if row else None

def migrate():
    if db.get_setting("ai_connections_migrated",False):return
    original={k:prefs.get(k) for k in ("ai_provider","ai_model","ai_base_url","chatgpt_model")}
    db.set_setting("ai_configuration_backup",original)
    kind=original["ai_provider"]
    if kind=="compatible" and original["ai_base_url"]:
        url=original["ai_base_url"].rstrip("/")
        for ident,meta in CATALOG.items():
            if ident not in {"chatgpt","compatible","ollama","lmstudio"} and url in {meta["base_url"],meta["base_url"]+"/openai",meta["base_url"]+"/v1"}:
                kind=ident;old=store.get("ai_api_key_compatible")
                if old and not store.get("ai_api_key_"+kind):
                    store.set("ai_api_key_"+kind,old)
                    if store.get("ai_api_key_"+kind)!=old:raise ValueError("Credential migration could not be verified. Original configuration retained.")
                break
    for ident,meta in CATALOG.items():
        if ident==kind or store.get("ai_api_key_"+ident):
            model=original["chatgpt_model"] if ident=="chatgpt" else original["ai_model"] if ident==kind else ""
            base=original["ai_base_url"] if ident==kind and ident in {"compatible","ollama","lmstudio"} else meta["base_url"]
            data=Connection(name=meta["name"],model=model or "",base_url=base or meta["base_url"],local=ident in {"ollama","lmstudio"}).model_dump()
            if ident in {"compatible","ollama","lmstudio"} and store.get("ai_api_key_"+ident) and not store.get("ai_endpoint_"+ident):store.set("ai_endpoint_"+ident,data["base_url"])
            db.execute("INSERT OR IGNORE INTO ai_connections(id,config) VALUES(?,?)",(ident,json.dumps(data)))
    if kind!=original["ai_provider"]:db.set_setting("ai_provider",kind)
    db.set_setting("ai_connections_migrated",True)

def validate_connection(kind,data):
    if kind not in CATALOG:raise ValueError("Unknown AI provider.")
    meta=CATALOG[kind]; value=Connection.model_validate(data).model_dump()
    value["name"]=value["name"] or meta["name"]
    value["base_url"]=validate_url(value["base_url"] or meta["base_url"])
    if kind not in {"compatible","ollama","lmstudio"}:
        if value["base_url"]!=meta["base_url"]:raise ValueError("This provider uses its official endpoint. Use Custom for a different server.")
        value["local"]=False
    if value["manual_model"] and kind!="compatible":raise ValueError("Manual model testing is only available for custom compatible endpoints.")
    if value["local"] and not is_loopback(value["base_url"]):raise ValueError("Local providers must use a loopback address on this computer.")
    return value

def build(kind,data=None,key=None):
    from .ai_adapters import ADAPTERS
    data=data or config(kind) or {}
    if kind=="chatgpt":
        from .chatgpt_provider import ChatGPTPlanProvider
        return ChatGPTPlanProvider(data.get("model",prefs.get("chatgpt_model")))
    if kind not in ADAPTERS:raise ValueError("Choose an AI provider in Settings > AI Providers.")
    bound=store.get("ai_endpoint_"+kind)
    if key is None and bound and bound != (data.get("base_url") or CATALOG[kind]["base_url"]):
        raise ValueError("This key is bound to a different endpoint. Re-enter the correct key for this server.")
    obj=ADAPTERS[kind](data.get("model", ""),store.get("ai_api_key_"+kind) if key is None else key,data.get("base_url", ""))
    obj.connection_config=data
    cached=db.one("SELECT models FROM ai_model_cache WHERE connection_id=?",(kind,))
    obj.model_metadata=next((m for m in json.loads(cached["models"]) if m["id"]==obj.model),{}) if cached else {}
    return obj

def selected_provider(feature="default"):
    p=policy();kind=p.overrides.get(feature) or prefs.get("ai_provider")
    data=config(kind)
    if data is None:
        data={"model":prefs.get("chatgpt_model") if kind=="chatgpt" else prefs.get("ai_model"),"base_url":prefs.get("ai_base_url") if kind in {"ollama","compatible","lmstudio"} else CATALOG.get(kind,{}).get("base_url", ""),"local":kind in {"ollama","lmstudio"}}
    if not data.get("enabled",True):raise ValueError("This AI connection is disabled. Choose another provider in Settings.")
    data=dict(data)
    if feature in p.feature_models:data["model"]=p.feature_models[feature]
    if p.local_only and (kind not in {"ollama","lmstudio","compatible"} or not data.get("local") or not is_loopback(data.get("base_url",""))):raise ValueError("Local AI Only is enabled. Select a verified local model; cloud AI and cloud fallback are blocked.")
    obj=build(kind,data);obj.feature=feature;obj.managed=True
    return obj

async def enforce_local(obj):
    p=policy()
    if not p.local_only:return
    if not is_loopback(obj.base_url) or not getattr(obj,"connection_config",{}).get("local"):
        raise ValueError("Local AI Only blocks this provider.")
    if obj.kind=="ollama":
        import httpx
        from .errors import request
        # Cloud aliases can be renamed. Inspect model metadata rather than trusting its name.
        async with httpx.AsyncClient(timeout=20,follow_redirects=False) as client:
            response=await request(client,"POST",obj.base_url+"/api/show","Ollama",json={"model":obj.model})
        data=response.json()
        if data.get("remote_host") or data.get("remote_model") or not data.get("model_info"):
            raise ValueError("Local-only mode requires an installed Ollama model with local model metadata. Cloud or unverifiable models are blocked.")
    # A local custom server is controlled by the user; it must be configured not to proxy cloud inference.

def fallback_provider(current,error):
    p=policy()
    if not p.fallback_enabled or p.local_only or not p.fallback or p.fallback==current.kind:return None
    if error.status not in {0,408,429} and not 500<=error.status<=599:return None
    # Billing-like 429s must never trigger another charge.
    if getattr(error,"billing",False):return None
    data=config(p.fallback)
    if not data or not data.get("enabled") or p.fallback=="chatgpt":return None
    obj=build(p.fallback,data);obj.managed=True;obj.feature=current.feature;obj.allow_fallback=False
    db.set_setting("ai_last_fallback",{"from":current.kind,"to":p.fallback,"at":db.now()})
    return obj

def writing_context():
    p=policy();out={"interests":prefs.get("interests")}
    if p.send_voice:out.update(voice=prefs.get("voice"),brand_voice=prefs.get("brand_voice"))
    if p.send_profile:out["my_profile"]=prefs.get("my_profile")
    if p.send_product:out["product"]=prefs.get("product")
    if p.send_conversation:out["application_memory"]=db.rows("SELECT key,value FROM application_memory")
    return out

def record_request(obj,req,result,started):
    if not policy().usage_log:return
    usage=result.usage if result else {}
    def count(*names):
        for name in names:
            v=usage.get(name)
            if isinstance(v,int) and not isinstance(v,bool) and v>=0:return v
        return None
    prompt=None
    if policy().prompt_history:
        from .command_bus import redact
        prompt=redact(json.dumps({"system":req.system,"user":req.user}))[:32000]
    db.execute("INSERT INTO ai_requests(provider,model,feature,created_at,duration_ms,input_tokens,output_tokens,status,finish_reason,request_id,prompt) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (obj.kind,result.model if result else obj.model,obj.feature,db.now(),int((time.monotonic()-started)*1000),count("input_tokens","prompt_tokens"),count("output_tokens","completion_tokens"),"success" if result else "failed",result.finish_reason if result else "",(result.request_id if result else "")[:150],prompt))

async def models(kind,data=None,key=None,refresh=False):
    data=data or config(kind) or {"base_url":CATALOG[kind]["base_url"],"model":""}
    # Fingerprint only non-secret endpoint configuration. Key changes explicitly invalidate cache.
    fingerprint=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
    row=db.one("SELECT * FROM ai_model_cache WHERE connection_id=?",(kind,))
    if not refresh and key is None and row and row["fingerprint"]==fingerprint and time.time()-row["fetched_at"]<21600:return json.loads(row["models"])
    obj=build(kind,data,key)
    if kind=="chatgpt":items=[{"id":x["slug"],"name":x["display_name"]} for x in await obj.get_models()]
    elif kind=="compatible" and data.get("manual_model"):
        if not data.get("model"):raise ValueError("Enter the model ID your custom server provides.")
        await enforce_local(obj)
        await obj.complete("Connection test. Respond with OK only.","OK")
        items=[{"id":obj.model,"name":obj.model,"status":"Generation tested; catalog unavailable"}]
    else:items=await obj.list_models()
    if key is None:db.execute("INSERT OR REPLACE INTO ai_model_cache VALUES(?,?,?,?)",(kind,fingerprint,time.time(),json.dumps(items)))
    return items
