"""Provider settings stay behind the existing localhost session and CSRF boundary."""
import json
from fastapi import APIRouter, HTTPException
from . import ai_connections as ai, database as db, preferences as prefs
from .ai_registry import CATALOG
from .secrets import store
router=APIRouter(prefix="/api/ai")

def known(kind):
    if kind not in CATALOG:raise HTTPException(404,"Unknown AI provider.")

@router.get("/providers")
def providers():
    result=[]
    for kind,meta in sorted(CATALOG.items(),key=lambda pair:pair[1]["name"].casefold()):
        row=db.one("SELECT health FROM ai_connections WHERE id=?",(kind,))
        result.append({**meta,"config":ai.config(kind),"key_mask":store.masked("ai_api_key_"+kind),"health":json.loads(row["health"]) if row else {}})
    return {"providers":result,"primary":prefs.get("ai_provider"),"policy":ai.policy().model_dump(),"last_fallback":db.get_setting("ai_last_fallback")}

@router.post("/providers/{kind}/test")
async def test(kind:str,data:ai.ConnectionInput):
    known(kind)
    checked=ai.validate_connection(kind,data.model_dump(exclude={"api_key"}))
    old=ai.config(kind)
    if old and old["base_url"]!=checked["base_url"] and data.api_key is None and store.get("ai_api_key_"+kind):raise ValueError("Changing the endpoint requires entering its key again. Saved credentials will not be sent to a new host.")
    key=data.api_key.get_secret_value().strip() if data.api_key is not None else None
    try:items=await ai.models(kind,checked,key,refresh=True)
    except Exception:
        if old:db.execute("UPDATE ai_connections SET health=? WHERE id=?",(json.dumps({"ok":False,"checked_at":db.now()}),kind))
        raise
    db.set_setting("ai_backoff_"+kind,{})
    return {"ok":True,"models":items,"message":"Manual model generation test passed." if checked.get("manual_model") else "Connection verified through model discovery. Generation access may also require credits."}

@router.put("/providers/{kind}")
async def save(kind:str,data:ai.ConnectionInput):
    known(kind);checked=ai.validate_connection(kind,data.model_dump(exclude={"api_key"}));old=ai.config(kind)
    if old and old["base_url"]!=checked["base_url"] and data.api_key is None and store.get("ai_api_key_"+kind):raise ValueError("Re-enter the key for the new endpoint before saving.")
    key=data.api_key.get_secret_value().strip() if data.api_key is not None else None
    items=await ai.models(kind,checked,key,refresh=True)
    if checked["model"] not in {m["id"] for m in items}:raise ValueError("Choose a model from the discovered catalog before saving.")
    if key is not None:
        store.set("ai_api_key_"+kind,key)
        store.set("ai_endpoint_"+kind,checked["base_url"])
        if store.get("ai_api_key_"+kind)!=key:raise ValueError("Credential storage verification failed. Configuration was not saved.")
    db.execute("INSERT INTO ai_connections(id,config,health) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET config=excluded.config,health=excluded.health",(kind,json.dumps(checked),json.dumps({"ok":True,"checked_at":db.now()})))
    db.execute("DELETE FROM ai_model_cache WHERE connection_id=?",(kind,))
    if prefs.get("ai_provider")==kind:
        activate(kind);db.set_setting("ai_pause",{})
    import hashlib,time
    fingerprint=hashlib.sha256(json.dumps(checked,sort_keys=True).encode()).hexdigest()
    db.execute("INSERT OR REPLACE INTO ai_model_cache VALUES(?,?,?,?)",(kind,fingerprint,time.time(),json.dumps(items)))
    return {"saved":True,"message":"AI provider saved","key_mask":store.masked("ai_api_key_"+kind)}

@router.post("/providers/{kind}/activate")
def activate(kind:str):
    known(kind);data=ai.config(kind)
    if kind=="chatgpt":
        prefs.save({"ai_provider":kind});return {"selected":kind}
    if not data or not data["enabled"] or not data["model"]:raise ValueError("Configure and enable this provider first.")
    if ai.policy().local_only and not data["local"]:raise ValueError("Local AI Only blocks cloud provider selection.")
    prefs.save({"ai_provider":kind,"ai_model":data["model"],"ai_base_url":data["base_url"]})
    db.set_setting("ai_health",json.loads(db.one("SELECT health FROM ai_connections WHERE id=?",(kind,))["health"]))
    return {"selected":kind}

@router.post("/providers/{kind}/disable")
def disable(kind:str):
    known(kind);data=ai.config(kind)
    if not data:raise ValueError("This provider has not been configured.")
    data["enabled"]=False;db.execute("UPDATE ai_connections SET config=? WHERE id=?",(json.dumps(data),kind))
    return {"disabled":True}

@router.delete("/providers/{kind}/key")
def delete_key(kind:str):
    known(kind);store.delete("ai_api_key_"+kind);store.delete("ai_endpoint_"+kind)
    db.execute("DELETE FROM ai_model_cache WHERE connection_id=?",(kind,))
    db.execute("UPDATE ai_connections SET health='{}' WHERE id=?",(kind,))
    return {"deleted":True}

@router.get("/providers/{kind}/models")
async def models(kind:str,refresh:bool=False):known(kind);return await ai.models(kind,refresh=refresh)

@router.put("/policy")
def policy(data:ai.Policy):
    db.set_setting("ai_policy",data.model_dump());return data.model_dump()

@router.get("/context-preview")
def preview():
    return {"context":ai.writing_context(),"note":"Generation also includes your selected post, brief or image and the app's truthfulness rules. Terminal commands include the app state needed for the requested action. Secrets are never included."}

@router.get("/usage")
def usage():return db.rows("SELECT id,provider,model,feature,created_at,duration_ms,input_tokens,output_tokens,status,finish_reason FROM ai_requests ORDER BY id DESC LIMIT 300")

@router.delete("/usage")
def clear_usage():db.execute("DELETE FROM ai_requests");return {"deleted":True}
