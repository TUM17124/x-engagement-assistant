import base64
import hashlib
import secrets
import time
from urllib.parse import urlencode

import httpx

from .config import settings
from .storage import load_tokens, save_tokens

AUTH_URL = "https://x.com/i/oauth2/authorize"
TOKEN_URL = "https://api.x.com/2/oauth2/token"
API = "https://api.x.com/2"

SCOPES = "tweet.read tweet.write users.read offline.access"

def make_pkce():
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge

def make_authorize_url(state: str, challenge: str):
    params = {
        "response_type": "code",
        "client_id": settings.x_client_id,
        "redirect_uri": settings.x_redirect_uri,
        "scope": SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return AUTH_URL + "?" + urlencode(params)

def _basic_auth_header():
    raw = f"{settings.x_client_id}:{settings.x_client_secret}".encode()
    return "Basic " + base64.b64encode(raw).decode()

async def exchange_code(code: str, verifier: str):
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if settings.x_client_secret:
        headers["Authorization"] = _basic_auth_header()

    data = {
        "code": code,
        "grant_type": "authorization_code",
        "client_id": settings.x_client_id,
        "redirect_uri": settings.x_redirect_uri,
        "code_verifier": verifier,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(TOKEN_URL, headers=headers, data=data)
        r.raise_for_status()
        payload = r.json()

    expires_at = int(time.time()) + int(payload.get("expires_in", 7200)) - 60
    save_tokens(payload["access_token"], payload.get("refresh_token"), expires_at)
    return payload

async def refresh_if_needed():
    token = load_tokens()
    if not token:
        raise RuntimeError("X account is not connected.")
    if token.get("expires_at") and int(token["expires_at"]) > int(time.time()):
        return token["access_token"]

    refresh_token = token.get("refresh_token")
    if not refresh_token:
        return token["access_token"]

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if settings.x_client_secret:
        headers["Authorization"] = _basic_auth_header()

    data = {
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "client_id": settings.x_client_id,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(TOKEN_URL, headers=headers, data=data)
        r.raise_for_status()
        payload = r.json()

    expires_at = int(time.time()) + int(payload.get("expires_in", 7200)) - 60
    save_tokens(
        payload["access_token"],
        payload.get("refresh_token", refresh_token),
        expires_at,
    )
    return payload["access_token"]

async def me():
    token = await refresh_if_needed()
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{API}/users/me",
            params={"user.fields": "username,name,verified"},
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        return r.json()["data"]

async def create_post(text: str):
    token = await refresh_if_needed()
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{API}/tweets",
            json={"text": text},
            headers={"Authorization": f"Bearer {token}"},
        )
        if r.status_code >= 400:
            raise RuntimeError(f"X API {r.status_code}: {r.text}")
        return r.json()

async def create_quote(text: str, tweet_id: str):
    token = await refresh_if_needed()
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{API}/tweets",
            json={"text": text, "quote_tweet_id": tweet_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        if r.status_code >= 400:
            raise RuntimeError(f"X API {r.status_code}: {r.text}")
        return r.json()

async def create_reply(text: str, tweet_id: str):
    token = await refresh_if_needed()
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{API}/tweets",
            json={
                "text": text,
                "reply": {"in_reply_to_tweet_id": tweet_id},
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        if r.status_code >= 400:
            raise RuntimeError(f"X API {r.status_code}: {r.text}")
        return r.json()
