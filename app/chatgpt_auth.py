"""Official SIWC public-client flow. Credentials never cross the HTTP UI boundary."""
import asyncio
import base64
import hashlib
import json
import secrets
import time
import uuid
import webbrowser
from urllib.parse import urlencode, urlsplit, parse_qs
import httpx
import jwt
from .secrets import store
from .paths import data_dir
from . import database as db

ISSUER = "https://auth.openai.com"
RESOURCE = "https://api.openai.com/v1"
SCOPE = "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"
USAGE_URL = "https://chatgpt.com/settings/usage"
TERMINAL_REFRESH = {"invalid_grant", "invalid_refresh_token", "token_expired",
    "refresh_token_expired", "refresh_token_invalidated", "refresh_token_reused"}

class ChatGPTError(ValueError):
    def __init__(self, message, state="Temporary service error", code="", status=0):
        super().__init__(message)
        self.state, self.code, self.status = state, code, status

class ChatGPTAuthService:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.server = None
        self.pending = None
        self.timer = None
        self.refreshing = False

    def _load(self):
        return json.loads(store.get("chatgpt_connections") or '{"active":"","profiles":{}}')

    def _save(self, data):
        store.set("chatgpt_connections", json.dumps(data))

    def _selected(self):
        data = self._load()
        return data, data["profiles"].get(data["active"], {})

    def host_id(self):
        path = data_dir() / "chatgpt-host.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))["host_id"]
            parsed = uuid.UUID(value.removeprefix("urn:uuid:"))
            if not value.startswith("urn:uuid:") or parsed.version != 4:
                raise ValueError()
            return value
        except FileNotFoundError:
            value = "urn:uuid:" + str(uuid.uuid4())
            try:
                with path.open("x", encoding="utf-8") as stream:
                    json.dump({"host_id": value}, stream)
            except FileExistsError:
                return self.host_id()
            return value
        except (ValueError, KeyError):
            raise ValueError("The installation identifier is invalid. Restore chatgpt-host.json from your local backup.") from None

    def get_connection_status(self):
        data, profile = self._selected()
        connected = bool(profile.get("access_token"))
        enabled = connected and "chatgpt.tokens.use.direct" in profile.get("scopes", [])
        state = profile.get("state") or ("Connected" if enabled else "Plan usage disabled" if connected else "Disconnected")
        if self.refreshing:
            state = "Refreshing"
        return {"connected": connected, "plan_usage": enabled, "state": state,
            "message": profile.get("message", ""), "active": data["active"],
            "profile": {k: profile.get(k, "") for k in ("name", "email", "picture")},
            "profiles": [{"id": key, "name": p.get("name", ""), "email": p.get("email", ""),
                          "connected": bool(p.get("access_token"))}
                         for key, p in data["profiles"].items()],
            "signing_in": bool(self.pending), "manage_usage_url": USAGE_URL}

    def get_profile(self):
        return self.get_connection_status()["profile"]

    def has_plan_usage_permission(self):
        return self.get_connection_status()["plan_usage"]

    def _state(self, state, message="", blocked=False, retry_after=0):
        data, profile = self._selected()
        if profile:
            profile.update(state=state, message=message, blocked=blocked,
                           retry_at=time.time() + retry_after if retry_after else 0)
            self._save(data)
            if state in {"Usage limit reached","Authorization expired","Plan usage disabled"}:
                from .workspace import notify
                marker="chatgpt_notification_state"
                if db.get_setting(marker)!=state:
                    notify(message or "ChatGPT needs attention in AI Settings.")
                    db.set_setting(marker,state)

    async def _discovery(self):
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(ISSUER + "/.well-known/openid-configuration")
        if response.status_code != 200:
            raise ChatGPTError("OpenAI sign-in is temporarily unavailable.")
        data = response.json()
        if data.get("issuer") != ISSUER:
            raise ChatGPTError("OpenAI identity discovery could not be verified.")
        for key in ("authorization_endpoint", "token_endpoint", "jwks_uri", "revocation_endpoint"):
            url = urlsplit(data.get(key, ""))
            if url.scheme != "https" or url.netloc != "auth.openai.com" or url.fragment or url.username:
                raise ChatGPTError("OpenAI identity discovery returned an unexpected endpoint.")
        return data

    async def connect(self, profile_id=None, new_profile=False, enable_plan=False):
        async with self.lock:
            await self.close_listener()
            data = self._load()
            key = str(uuid.uuid4()) if new_profile else (profile_id or data["active"] or str(uuid.uuid4()))
            if profile_id and profile_id not in data["profiles"]:
                raise ValueError("Choose a saved ChatGPT account.")
            profile = data["profiles"].get(key, {})
            config = await self._discovery()
            self.server = await asyncio.start_server(self._callback_connection, "127.0.0.1", 0, limit=16384)
            port = self.server.sockets[0].getsockname()[1]
            verifier = secrets.token_urlsafe(64)
            state, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            redirect = f"http://127.0.0.1:{port}/auth/chatgpt/callback"
            client_id = profile.get("client_id") or "dynamic_agent_client"
            self.pending = {"key": key, "state": state, "nonce": nonce, "verifier": verifier,
                "redirect": redirect, "client_id": client_id, "expires": time.time()+600, "config": config}
            query = {"client_id": client_id, "ext_agent_host_id": self.host_id(), "response_type": "code",
                "redirect_uri": redirect, "scope": SCOPE, "resource": RESOURCE, "state": state, "nonce": nonce,
                "code_challenge_method": "S256",
                "code_challenge": base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")}
            if client_id == "dynamic_agent_client":
                query["agent_name_hint"] = "Social Engagement Command Center"
            else:
                if profile.get("id_token"): query["id_token_hint"] = profile["id_token"]
                if profile.get("email"): query["login_hint"] = profile["email"]
            if enable_plan: query["prompt"] = "consent"
            # Only the backend opens this URL, which can contain a retained ID token hint.
            try:
                opened = await asyncio.to_thread(webbrowser.open, config["authorization_endpoint"]+"?"+urlencode(query))
                if not opened: raise ValueError("The default browser could not be opened. Set a default browser and reconnect.")
            except Exception:
                await self.close_listener()
                raise
            self.timer = asyncio.create_task(self._expire())
            return self.get_connection_status()

    async def _expire(self):
        await asyncio.sleep(600)
        await self.close_listener()

    async def close_listener(self):
        self.pending = None
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
        if self.timer and self.timer is not asyncio.current_task():
            self.timer.cancel()
        self.timer = None

    async def _callback_connection(self, reader, writer):
        ok = False
        try:
            header = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 15)
            first = header.split(b"\r\n", 1)[0].decode("ascii")
            method, target, _ = first.split(" ", 2)
            url = urlsplit(target)
            if method != "GET" or url.path != "/auth/chatgpt/callback":
                raise ValueError("Invalid callback.")
            raw = parse_qs(url.query, keep_blank_values=True)
            if any(len(v) != 1 for v in raw.values()): raise ValueError("Duplicate callback parameters.")
            await self.handle_callback({k:v[0] for k,v in raw.items()})
            ok = True
        except Exception:
            pass  # Never log OAuth callback URLs or credentials.
        body = ("ChatGPT connected. Return to Social Engagement Command Center." if ok else
                "ChatGPT sign-in was not completed. Return to the app and reconnect.").encode()
        try:
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\nCache-Control: no-store\r\nReferrer-Policy: no-referrer\r\nConnection: close\r\nContent-Length: "+str(len(body)).encode()+b"\r\n\r\n"+body)
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def _verify_identity(self, encoded, client_id, nonce=None):
        config = await self._discovery()
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(config["jwks_uri"])
        if response.status_code != 200: raise ChatGPTError("OpenAI identity keys are temporarily unavailable.")
        try:
            header = jwt.get_unverified_header(encoded)
            if header.get("alg") != "RS256": raise ValueError()
            keys = [k for k in response.json()["keys"] if k.get("kid") == header.get("kid") and k.get("kty") == "RSA"]
            if len(keys) != 1: raise ValueError()
            key = jwt.PyJWK.from_dict(keys[0], algorithm="RS256").key
            identity = jwt.decode(encoded, key, algorithms=["RS256"], audience=client_id, issuer=ISSUER,
                options={"require":["iss","sub","aud","exp","iat"]})
            if nonce is not None and not secrets.compare_digest(identity.get("nonce",""), nonce): raise ValueError()
            if not isinstance(identity["sub"],str) or not identity["sub"]: raise ValueError()
            return identity
        except (jwt.PyJWTError, KeyError, ValueError, TypeError):
            raise ChatGPTError("ChatGPT identity verification failed. Reconnect.", "Authorization expired") from None

    async def _token_request(self, body, refreshing=False):
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(ISSUER+"/api/accounts/oauth/token", data=body)
        if response.status_code != 200:
            try:
                payload = response.json()
                code = payload.get("error","")
                if isinstance(code,dict): code=code.get("code","")
            except ValueError: code=""
            if refreshing and code in TERMINAL_REFRESH:
                data, profile = self._selected()
                for key in ("access_token","refresh_token","id_token"): profile.pop(key,None)
                profile.update(state="Authorization expired", message="ChatGPT connection needs to be renewed.", blocked=True)
                self._save(data)
            raise ChatGPTError("ChatGPT connection needs to be renewed." if code in TERMINAL_REFRESH else
                "ChatGPT authorization could not be renewed. Retry later or reconnect.",
                "Authorization expired" if code in TERMINAL_REFRESH else "Temporary service error", code)
        return response.json()

    def _merge_tokens(self, profile, tokens, initial=False):
        if str(tokens.get("token_type","")).lower() != "bearer" or not tokens.get("access_token"):
            raise ChatGPTError("OpenAI returned an incomplete credential set.")
        scopes = tokens["scope"].split() if "scope" in tokens else ([] if initial else profile.get("scopes",[]))
        expires = int(tokens.get("expires_in",0))
        if expires <= 0: raise ChatGPTError("OpenAI returned an invalid token expiry.")
        updated = dict(profile)
        updated.update({k:tokens[k] for k in ("access_token","refresh_token","id_token") if tokens.get(k)})
        updated.update(scopes=scopes, expires_at=time.time()+expires, earliest_refresh_at=tokens.get("earliest_refresh_at"),
                       state="Connected" if "chatgpt.tokens.use.direct" in scopes else "Plan usage disabled",
                       message="", blocked=False, retry_at=0)
        return updated

    async def handle_callback(self, values):
        async with self.lock:
            pending = self.pending
            if not pending or pending["expires"] < time.time() or not secrets.compare_digest(values.get("state",""), pending["state"]):
                raise ValueError("Invalid or expired ChatGPT callback.")
            await self.close_listener()  # One use, including denied callbacks.
            if values.get("error"): raise ValueError("ChatGPT authorization was not granted.")
            client_id = values.get("client_id") or pending["client_id"]
            if client_id == "dynamic_agent_client" or not client_id or len(client_id)>256:
                raise ValueError("ChatGPT registration was incomplete.")
            if pending["client_id"] != "dynamic_agent_client" and client_id != pending["client_id"]:
                raise ValueError("ChatGPT registration changed unexpectedly.")
            if not values.get("code"): raise ValueError("Authorization code missing.")
            data = self._load()
            previous = data["profiles"].get(pending["key"], {})
            previous["client_id"] = client_id
            data["profiles"][pending["key"]] = previous
            self._save(data)  # Retain issued registration even if code exchange fails.
            tokens = await self._token_request({"grant_type":"authorization_code","client_id":client_id,
                "code":values["code"],"code_verifier":pending["verifier"],"redirect_uri":pending["redirect"],"resource":RESOURCE})
            identity = await self._verify_identity(tokens.get("id_token",""),client_id,pending["nonce"])
            if previous.get("subject") and previous["subject"] != identity["sub"]:
                raise ValueError("The signed-in ChatGPT identity does not match the selected account.")
            updated = self._merge_tokens(previous,tokens,initial=True)
            updated.update(subject=identity["sub"],issuer=ISSUER,name=identity.get("name",""),
                           email=identity.get("email",""),picture=identity.get("picture",""))
            data["profiles"][pending["key"]] = updated
            data["active"] = pending["key"]
            self._save(data)
            db.set_setting("ai_pause",{})
            db.set_setting("chatgpt_models",[])
            return self.get_connection_status()

    async def select(self, key):
        async with self.lock:
            data = self._load()
            if key not in data["profiles"]: raise ValueError("ChatGPT account not found.")
            data["active"] = key
            self._save(data)
            db.set_setting("chatgpt_models",[])
            db.set_setting("ai_pause",{})
            return self.get_connection_status()

    async def get_access_token_for_internal_use(self):
        async with self.lock:
            data, profile = self._selected()
            if not profile.get("access_token"):
                raise ChatGPTError("Continue with ChatGPT to connect your account.", "Disconnected")
            if profile.get("blocked") or profile.get("retry_at",0)>time.time():
                raise ChatGPTError(profile.get("message") or "ChatGPT usage is paused. Retry from Settings.", profile.get("state",""))
            if "chatgpt.tokens.use.direct" not in profile.get("scopes",[]):
                raise ChatGPTError("Enable ChatGPT plan usage before generating content.", "Plan usage disabled")
            if profile.get("expires_at",0) <= time.time()+60:
                profile = await self._refresh(data,profile)
            return profile["access_token"]

    async def _refresh(self, data, profile):
        if not profile.get("refresh_token"):
            self._state("Authorization expired","ChatGPT connection needs to be renewed.",True)
            raise ChatGPTError("ChatGPT connection needs to be renewed.", "Authorization expired")
        self.refreshing = True
        try:
            tokens = await self._token_request({"grant_type":"refresh_token","client_id":profile["client_id"],
                "refresh_token":profile["refresh_token"],"resource":RESOURCE}, refreshing=True)
            if tokens.get("id_token"):
                identity = await self._verify_identity(tokens["id_token"],profile["client_id"])
                if identity["sub"] != profile["subject"]: raise ChatGPTError("ChatGPT account changed during renewal.")
            updated = self._merge_tokens(profile,tokens)
            data["profiles"][data["active"]] = updated
            self._save(data)  # Atomic token + rotating refresh-token replacement.
            return updated
        except httpx.RequestError:
            self._state("Temporary service error","ChatGPT renewal is temporarily unavailable. Credentials are retained; retry later.",False,60)
            raise ChatGPTError("ChatGPT renewal is temporarily unavailable. Retry later.") from None
        except ChatGPTError as error:
            if error.code not in TERMINAL_REFRESH:
                self._state(error.state,str(error),error.code=="invalid_client",60)
            raise
        finally:
            self.refreshing = False

    async def refresh_access_token(self):
        async with self.lock:
            data, profile = self._selected()
            return await self._refresh(data,profile)  # Backend only; not exposed by routes.

    async def disconnect(self):
        async with self.lock:
            await self.close_listener()
            data, profile = self._selected()
            confirmed = not profile.get("refresh_token")
            if not confirmed:
                try:
                    config = await self._discovery()
                    async with httpx.AsyncClient(timeout=20) as client:
                        response = await client.post(config["revocation_endpoint"], data={
                            "token":profile["refresh_token"],"token_type_hint":"refresh_token","client_id":profile["client_id"]})
                    confirmed = response.status_code == 200
                except (httpx.HTTPError, ChatGPTError):
                    pass
            for key in ("access_token","refresh_token","id_token"): profile.pop(key,None)
            if profile: profile.update(state="Disconnected",message="",blocked=False)
            self._save(data)
            db.set_setting("chatgpt_models",[])
            return {"disconnected":True,"remote_revocation_confirmed":confirmed,
                "message":"Signed out." if confirmed else "Signed out locally. Remote revocation was not confirmed; disconnect the app in ChatGPT Settings."}

    def retry(self):
        self._state("Connected" if self.has_plan_usage_permission() else "Plan usage disabled")
        db.set_setting("ai_pause",{})
        return self.get_connection_status()

auth = ChatGPTAuthService()
