import json
from urllib.parse import urlsplit
from fastapi import APIRouter,Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel,Field
from .. import database as db,preferences as prefs
from ..secrets import store
from ..storage import load_tokens
from .catalog import CATALOG,definition,capabilities
from .registry import provider
from . import oauth

router=APIRouter()

class ConnectionConfig(BaseModel):
    client_id:str=Field(default="",max_length=1000)
    redirect_uri:str=Field(max_length=2048)
    client_secret:str=Field(default="",max_length=8192)

@router.get("/api/social/accounts")
def accounts():
    result=[]
    for name,spec in CATALOG.items():
        p=provider(name)
        account=p.account
        connected=bool(load_tokens()) if name=="x" else bool(account and p.tokens().get("access_token"))
        if name=="x":
            profile=db.get_setting("x_profile") or {}
            account={"name":profile.get("username",""),"avatar":profile.get("profile_image_url",""),"permissions":"tweet.read tweet.write users.read offline.access","api_status":"Connected" if connected else "Not connected"}
        result.append({"platform":name,**spec,"account":account,"connected":connected,"capabilities":p.capabilities(),
            "config":oauth.config(name),"secret":store.masked("social_"+name+"_client_secret"),
            "paused":db.get_setting("social_pause_"+name,{}),
            "choices":[{"id":x["id"],"name":x["name"]} for x in json.loads(store.get("social_"+name+"_choices") or "[]")]})
    return result

@router.put("/api/social/accounts/{platform}/config")
def save_config(platform:str,data:ConnectionConfig):
    definition(platform)
    if platform=="x":raise ValueError("Use the existing X Connection settings.")
    url=urlsplit(data.redirect_uri)
    if url.username or url.password or url.query or url.fragment or not url.hostname:
        raise ValueError("Use a registered OAuth callback URL without credentials or query parameters.")
    if url.scheme!="https" and not (url.scheme=="http" and url.hostname in {"127.0.0.1","localhost"}):
        raise ValueError("Use HTTPS or the local desktop callback.")
    db.set_setting("social_config_"+platform,{"client_id":data.client_id.strip(),"redirect_uri":data.redirect_uri})
    if data.client_secret:store.set("social_"+platform+"_client_secret",data.client_secret.strip())
    return {"saved":True}

@router.post("/api/social/accounts/{platform}/connect")
def connect(platform:str):return {"url":provider(platform).connect()}

@router.get("/social/auth/{platform}/callback")
async def callback(platform:str,code:str="",state:str="",error:str=""):
    try:
        if error or not code:raise ValueError("Authorization was not completed.")
        result=await oauth.finish(platform,code,state)
        message="Select your Page in Connected Accounts." if result.get("select_account") else "Connected. Return to the desktop app."
        return RedirectResponse("/?ok="+__import__("urllib.parse",fromlist=["quote"]).quote(message)+"#settings",302)
    except Exception:
        return RedirectResponse("/?error=Could+not+connect.+Check+the+registered+OAuth+app+and+permissions.+No+password+is+required.#settings",302)

@router.post("/api/social/accounts/{platform}/complete")
async def complete(platform:str,data:dict):
    code,state=oauth.callback_values(platform,str(data.get("url","")))
    return await oauth.finish(platform,code,state)

@router.post("/api/social/accounts/facebook/select")
async def select_page(data:dict):
    choices=json.loads(store.get("social_facebook_choices") or "[]")
    page=next((x for x in choices if x["id"]==data.get("id")),None)
    if not page:raise ValueError("Choose a Page returned by your authorization.")
    previous=json.loads(store.get(oauth.key("facebook")) or "{}")
    tokens={"access_token":page["access_token"],"granted_scopes":previous.get("granted_scopes","")}
    store.set(oauth.key("facebook"),json.dumps(tokens))
    oauth.save_profile("facebook",{"id":page["id"],"name":page["name"]},tokens)
    store.delete("social_facebook_choices")
    return {"connected":True}

@router.post("/api/social/accounts/{platform}/test")
async def test_connection(platform:str):
    pause=db.get_setting("social_pause_"+platform,{})
    if pause.get("until","")>db.now():raise ValueError("Respect the provider's active rate-limit reset before testing again.")
    db.set_setting("social_pause_"+platform,{})
    p=provider(platform)
    profile=await p.health_check()
    if platform=="x":db.set_setting("x_profile",{"id":profile["id"],"username":profile["name"]})
    else:oauth.save_profile(platform,profile)
    return {"ok":True,"profile":profile}

@router.post("/api/social/accounts/{platform}/disconnect")
def disconnect(platform:str):
    provider(platform).disconnect()
    store.delete("social_"+platform+"_pending")
    return {"disconnected":True,"note":"Local tokens removed. You can also revoke this app in the platform's account settings."}

@router.post("/api/social/accounts/{platform}/secret/reveal")
def reveal(platform:str):
    definition(platform)
    return {"value":store.get("social_"+platform+"_client_secret"),"expires_in":15}

@router.delete("/api/social/accounts/{platform}/secret")
def delete_secret(platform:str):
    definition(platform);store.delete("social_"+platform+"_client_secret")
    return {"deleted":True}

@router.get("/api/social/usage")
def usage():
    return {"items":db.rows("SELECT platform,operation,status,COUNT(*) requests FROM social_usage WHERE substr(created_at,1,10)=? GROUP BY platform,operation,status",(db.now()[:10],)),
            "daily_cap":prefs.get("social_daily_request_cap"),"search":__import__("app.search",fromlist=["status"]).status(),
            "ai_today":db.one("SELECT COUNT(*) n FROM ai_usage WHERE substr(created_at,1,10)=?",(db.now()[:10],))["n"],
            "note":"Local request counts, not billing estimates. Quotas and access depend on each provider."}
