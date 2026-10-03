"""Official OpenRouter PKCE: browser grants a user-controlled key; only backend sees it."""
import base64, hashlib, secrets, time, json
from urllib.parse import urlencode
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from .secrets import store
from .errors import request
from . import database as db
from .ai_registry import CATALOG
router=APIRouter(); pending={}

@router.post("/api/ai/openrouter/connect")
def connect(req:Request):
    pending.clear()
    nonce=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(64)
    pending[nonce]=(verifier,time.monotonic()+300)
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    callback=str(req.base_url).rstrip("/")+"/auth/openrouter/"+nonce
    return {"url":"https://openrouter.ai/auth?"+urlencode({"callback_url":callback,"code_challenge":challenge,"code_challenge_method":"S256"})}

@router.get("/auth/openrouter/{nonce}",response_class=HTMLResponse)
async def callback(nonce:str,code:str=""):
    entry=pending.pop(nonce,None)
    if not entry or entry[1]<time.monotonic() or not code or len(code)>4096:
        return HTMLResponse("Authorization expired or invalid. Return to Settings and connect again.",status_code=400)
    async with httpx.AsyncClient(timeout=30,follow_redirects=False) as client:
        response=await request(client,"POST","https://openrouter.ai/api/v1/auth/keys","OpenRouter",json={"code":code,"code_verifier":entry[0],"code_challenge_method":"S256"})
    try:key=response.json()["key"]
    except (ValueError,KeyError,TypeError):raise ValueError("OpenRouter did not return a valid credential.") from None
    if not isinstance(key,str) or not key or len(key)>8192:raise ValueError("OpenRouter returned an invalid credential.")
    store.set("ai_api_key_openrouter",key)
    db.execute("DELETE FROM ai_model_cache WHERE connection_id='openrouter'")
    return HTMLResponse("<h1>OpenRouter authorization saved</h1><p>Return to Social Engagement, configure OpenRouter, test the connection and choose a model. Your primary provider was not changed.</p>")
