"""Browser OAuth; tokens and short-lived PKCE state use the OS vault."""
import base64
import hashlib
import json
import secrets
import time
from urllib.parse import urlencode,urlsplit,parse_qs
import httpx
from .catalog import definition
from .. import database as db
from ..secrets import store
from ..errors import check_response

def key(platform):return "social_"+platform+"_oauth"

def config(platform):
    definition(platform)
    result=db.get_setting("social_config_"+platform,{})
    result.setdefault("redirect_uri","http://127.0.0.1:8787/social/auth/"+platform+"/callback")
    return result

def begin(platform):
    spec=definition(platform);cfg=config(platform)
    if platform=="x":return "/auth/login"
    if not cfg.get("client_id"):raise ValueError("Save this provider's OAuth Client ID first. Never enter your social password.")
    state=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(64)
    store.set("social_"+platform+"_pending",json.dumps({"state":state,"verifier":verifier,"expires":time.time()+600}))
    params={"client_key" if platform=="tiktok" else "client_id":cfg["client_id"],"redirect_uri":cfg["redirect_uri"],"response_type":"code","state":state,"scope":spec["scopes"]}
    if spec.get("pkce"):
        digest=hashlib.sha256(verifier.encode()).digest()
        params.update(code_challenge=digest.hex() if spec["pkce"]=="hex" else base64.urlsafe_b64encode(digest).decode().rstrip("="),code_challenge_method="S256")
    if platform=="youtube":params.update(access_type="offline",prompt="consent")
    return spec["authorize"]+"?"+urlencode(params)

async def finish(platform,code,state):
    spec=definition(platform);cfg=config(platform)
    pending=json.loads(store.get("social_"+platform+"_pending") or "{}")
    if not pending or time.time()>pending["expires"] or not secrets.compare_digest(state,pending["state"]):
        raise ValueError("OAuth state is invalid or expired. Start Connect again.")
    store.delete("social_"+platform+"_pending")
    data={"grant_type":"authorization_code","code":code,"redirect_uri":cfg["redirect_uri"],
          "client_key" if platform=="tiktok" else "client_id":cfg["client_id"]}
    secret=store.get("social_"+platform+"_client_secret")
    if secret:data["client_secret"]=secret
    if spec.get("pkce"):data["code_verifier"]=pending["verifier"]
    async with httpx.AsyncClient(timeout=30) as client:
        r=await client.post(spec["token"],data=data)
    check_response(r,spec["name"])
    tokens=r.json()
    if not tokens.get("access_token"):raise ValueError("Authorization did not return a token. Check the registered app and permissions.")
    tokens["expires_at"]=time.time()+int(tokens.get("expires_in",3600))-60
    tokens["granted_scopes"]=tokens.get("scope","") or " ".join(tokens.get("permissions",[]))
    store.set(key(platform),json.dumps(tokens))
    db.set_setting("social_pause_"+platform,{})
    from .registry import provider
    p=provider(platform)
    if platform=="facebook":
        choices=await p.pages()
        store.set("social_facebook_choices",json.dumps(choices))
        return {"select_account":True,"choices":[{"id":x["id"],"name":x["name"]} for x in choices]}
    profile=await p.get_profile()
    save_profile(platform,profile,tokens)
    return {"connected":True}

def save_profile(platform,profile,tokens=None):
    tokens=tokens or json.loads(store.get(key(platform)) or "{}")
    scopes=tokens.get("granted_scopes") or ""
    db.execute("""INSERT INTO social_accounts(platform,account_id,name,avatar,permissions,api_status,last_sync)
      VALUES(?,?,?,?,?,'Connected',?) ON CONFLICT(platform) DO UPDATE SET account_id=excluded.account_id,
      name=excluded.name,avatar=excluded.avatar,permissions=excluded.permissions,api_status='Connected',last_sync=excluded.last_sync""",
      (platform,str(profile["id"]),profile.get("name",""),profile.get("avatar",""),scopes,db.now()))

async def access_token(platform):
    tokens=json.loads(store.get(key(platform)) or "{}")
    if not tokens.get("access_token"):raise ValueError("Connect this social account first.")
    if tokens.get("expires_at",0)>time.time() or not tokens.get("refresh_token"):
        return tokens["access_token"]
    spec=definition(platform);cfg=config(platform)
    data={"grant_type":"refresh_token","refresh_token":tokens["refresh_token"],
          "client_key" if platform=="tiktok" else "client_id":cfg.get("client_id","")}
    secret=store.get("social_"+platform+"_client_secret")
    if secret:data["client_secret"]=secret
    async with httpx.AsyncClient(timeout=30) as client:
        r=await client.post(spec["token"],data=data)
    check_response(r,spec["name"])
    new=r.json()
    if not new.get("access_token"):raise ValueError("Reconnect this account; token refresh was unavailable.")
    tokens.update(new);tokens["expires_at"]=time.time()+int(new.get("expires_in",3600))-60
    store.set(key(platform),json.dumps(tokens))
    return tokens["access_token"]

def callback_values(platform,url):
    expected=urlsplit(config(platform)["redirect_uri"]);actual=urlsplit(url)
    if (actual.scheme,actual.netloc,actual.path)!=(expected.scheme,expected.netloc,expected.path):
        raise ValueError("Paste the callback URL registered for this provider.")
    data=parse_qs(actual.query)
    if data.get("error"):raise ValueError("Authorization was declined. Start Connect again when ready.")
    if not data.get("code") or not data.get("state"):raise ValueError("The callback URL must include code and state.")
    return data["code"][0],data["state"][0]
