import asyncio
from contextlib import asynccontextmanager
import secrets
from urllib.parse import quote
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .paths import resources, VERSION
from . import database as db, preferences as prefs, x_api
from .storage import load_tokens, clear_tokens
from .settings_routes import router as settings_router
from .security import LocalSecurityMiddleware
from .errors import ServiceError
from .post_urls import parse_tweet_url

@asynccontextmanager
async def lifespan(app):
    db.init_db()
    prefs.bootstrap_dev_env()
    task = None
    try:
        from .workers import run_workers
        task = asyncio.create_task(run_workers())
    except ImportError:
        pass
    yield
    from .chatgpt_auth import auth
    from .terminal_routes import cancel_all
    await cancel_all()
    await auth.close_listener()
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

app = FastAPI(title="X Engagement Assistant", version=VERSION, lifespan=lifespan)
app.add_middleware(LocalSecurityMiddleware)
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret, same_site="lax")
templates = Jinja2Templates(directory=str(resources() / "templates"))
app.mount("/static", StaticFiles(directory=str(resources() / "static")), name="static")
app.include_router(settings_router)

from .chatgpt_auth import ChatGPTError

@app.exception_handler(ChatGPTError)
async def chatgpt_error(request, error):
    return JSONResponse({"error":str(error), "technical":f"ChatGPT HTTP {error.status}" if error.status else "ChatGPT: "+error.state,
        "hint":"Open Settings > AI Provider > ChatGPT Plan to check the account, plan permission and available models. API-key billing is a separate provider."},status_code=502)

@app.exception_handler(Exception)
async def unexpected_error(request, error):
    return JSONResponse({"error":"The app encountered an unexpected problem while completing this action.",
        "hint":"Your saved data is retained. Reopen the app and check History before repeating a publishing action.",
        "technical":"App HTTP 500"},status_code=500)

@app.exception_handler(RuntimeError)
async def runtime_error(request, error):
    return JSONResponse({"error": "The action could not be completed. Check your connection and settings."}, status_code=400)

@app.exception_handler(ValueError)
async def invalid(request, error):
    return JSONResponse({"error":str(error)},status_code=400)

@app.exception_handler(ServiceError)
async def service_error(request, error):
    return JSONResponse(error.details(),status_code=502)

@app.exception_handler(httpx.HTTPError)
async def network_error(request, error):
    # Never echo provider response bodies, request headers or credentials.
    return JSONResponse({"error":"Connection failed. Test the connection in Settings."},status_code=502)

@app.get("/health")
def health():
    return {"ok":True,"version":VERSION}

@app.get("/",response_class=HTMLResponse)
def home(request: Request):
    request.session.setdefault("csrf", secrets.token_urlsafe(32))
    return templates.TemplateResponse(request=request, name="desktop.html", context={"version":VERSION})

@app.get("/api/bootstrap")
def bootstrap(request: Request):
    request.session.setdefault("csrf", secrets.token_urlsafe(32))
    return {"csrf":request.session["csrf"],"version":VERSION,"settings":prefs.all_settings(),
            "profile":db.get_setting("x_profile"),"connected":bool(load_tokens())}

@app.get("/parse-tweet-url")
def parse_url(tweet_url: str=""):
    return parse_tweet_url(tweet_url)

@app.get("/auth/login")
async def auth_login(request: Request):
    if not settings.x_client_id:
        return RedirectResponse("/?error=Add+your+X+Client+ID+in+Settings",status_code=302)
    verifier, challenge = x_api.make_pkce()
    state = secrets.token_urlsafe(24)
    request.session["oauth_state"] = state
    request.session["pkce_verifier"] = verifier
    return RedirectResponse(x_api.make_authorize_url(state,challenge),status_code=302)

@app.get("/auth/callback")
async def auth_callback(request: Request, code: str="",state: str="",error: str=""):
    if error:
        return RedirectResponse("/?error=X+authorization+was+not+completed",status_code=302)
    expected = request.session.pop("oauth_state",None)
    verifier = request.session.pop("pkce_verifier",None)
    if not code or not expected or not secrets.compare_digest(state,expected) or not verifier:
        return RedirectResponse("/?error=Invalid+OAuth+callback",status_code=302)
    try:
        await x_api.exchange_code(code,verifier)
        try:
            db.set_setting("x_profile",await x_api.me())
        except (httpx.HTTPError, ServiceError):
            pass
        return RedirectResponse("/?ok=X+connected.+You+can+return+to+the+desktop+app.",status_code=302)
    except (httpx.HTTPError, ServiceError, RuntimeError):
        return RedirectResponse("/?error=Could+not+connect+X.+Check+your+credentials+and+callback+URL.",status_code=302)

@app.post("/auth/logout")
def logout():
    clear_tokens()
    db.set_setting("x_profile",None)
    db.set_setting("x_health",None)
    return {"ok":True}

@app.post("/api/health/x")
async def test_x():
    try:
        profile = await x_api.me()
    except Exception:
        db.set_setting("x_health", {"ok":False,"checked_at":db.now()})
        raise
    db.set_setting("x_health", {"ok":True,"checked_at":db.now()})
    db.set_setting("x_profile",profile)
    return {"ok":True,"profile":profile}

@app.post("/api/health/ai")
async def test_ai():
    from .providers import provider
    db.set_setting("ai_pause",{})
    try:
        await provider().health_check()
    except Exception:
        db.set_setting("ai_health", {"ok":False,"checked_at":db.now()})
        raise
    db.set_setting("ai_health",{"ok":True,"checked_at":db.now()})
    return {"ok":True}

from .workspace_routes import router as workspace_router
from .search_routes import router as search_router
app.include_router(workspace_router)
app.include_router(search_router)

from .desktop_control import router as desktop_router
app.include_router(desktop_router)

from .social.routes import router as social_router
app.include_router(social_router)

from .social.content_routes import router as social_content_router
from .media_routes import router as media_router
app.include_router(social_content_router)
app.include_router(media_router)

from .social.privacy import router as privacy_router
app.include_router(privacy_router)

from .chatgpt_routes import router as chatgpt_router
from .terminal_routes import router as terminal_router
app.include_router(chatgpt_router)
app.include_router(terminal_router)
