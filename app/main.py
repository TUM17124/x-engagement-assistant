import re
from urllib.parse import quote

import httpx

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .storage import (
    init_db, load_tokens, clear_tokens, log_action,
    action_count_today, duplicate_recent, recent_actions
)
from . import x_api
from .drafting import draft_reply
from .post_urls import parse_tweet_url

app = FastAPI(title="X Engagement Assistant")
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
templates = Jinja2Templates(directory="app/templates")

@app.on_event("startup")
def startup():
    init_db()

def ctx(request: Request, **extra):
    base = {
        "request": request,
        "connected": bool(load_tokens()),
        "today_count": action_count_today(),
        "daily_cap": settings.daily_write_cap,
        "actions": recent_actions(),
        "default_query": settings.default_query,
    }
    base.update(extra)
    return base

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    profile = None
    error = None
    if load_tokens():
        try:
            profile = await x_api.me()
        except Exception as e:
            error = str(e)
    return templates.TemplateResponse("index.html", ctx(request, profile=profile, error=error))

@app.get("/auth/login")
async def auth_login(request: Request):
    if not settings.x_client_id:
        return RedirectResponse("/?error=Missing+X_CLIENT_ID", status_code=302)
    verifier, challenge = x_api.make_pkce()
    import secrets
    state = secrets.token_urlsafe(24)
    request.session["oauth_state"] = state
    request.session["pkce_verifier"] = verifier
    return RedirectResponse(x_api.make_authorize_url(state, challenge), status_code=302)

@app.get("/auth/callback")
async def auth_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        return RedirectResponse(f"/?error={quote(error)}", status_code=302)
    if not code or state != request.session.get("oauth_state"):
        return RedirectResponse("/?error=Invalid+OAuth+callback", status_code=302)
    try:
        await x_api.exchange_code(code, request.session["pkce_verifier"])
        return RedirectResponse("/", status_code=302)
    except Exception as e:
        return RedirectResponse(f"/?error={quote(str(e))}", status_code=302)

@app.post("/auth/logout")
async def auth_logout():
    clear_tokens()
    return RedirectResponse("/", status_code=303)

@app.get("/parse-tweet-url")
async def parse_url(tweet_url: str = ""):
    try:
        return parse_tweet_url(tweet_url)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/draft", response_class=HTMLResponse)
async def draft(
    request: Request,
    tweet_url: str = Form(""),
    tweet_text: str = Form(""),
    author_username: str = Form(""),
    previous_draft: str = Form(""),
):
    source = dict(tweet_url=tweet_url, tweet_text=tweet_text,
                  author_username=author_username)
    try:
        source.update(parse_tweet_url(tweet_url))
        source["tweet_text"] = tweet_text.strip()
        source["author_username"] = author_username.strip().lstrip("@") or source["author_username"]
        if not source["tweet_text"]:
            raise ValueError("Paste the tweet text before generating a reply.")
        if not re.fullmatch(r"[A-Za-z0-9_]{1,15}", source["author_username"]):
            raise ValueError("Enter an author username using 1-15 letters, numbers, or underscores.")
    except ValueError as e:
        return templates.TemplateResponse(
            "index.html", ctx(request, **source, error=str(e)), status_code=400
        )
    try:
        text = await draft_reply(source["tweet_text"], source["author_username"])
    except Exception as e:
        if isinstance(e, httpx.HTTPStatusError):
            error = f"AI generation failed (HTTP {e.response.status_code}). Check your AI configuration and quota, then try again."
        elif isinstance(e, httpx.RequestError):
            error = "Could not reach the configured AI model. Please try again."
        elif isinstance(e, RuntimeError):
            error = str(e)
        else:
            error = "AI generation failed. Please try again."
        page = "draft.html" if previous_draft else "index.html"
        return templates.TemplateResponse(
            page, ctx(request, **source, draft=previous_draft, error=error), status_code=502
        )
    return templates.TemplateResponse(
        "draft.html", ctx(request, **source, draft=text)
    )


def ensure_can_write(text: str):
    if not text.strip():
        raise ValueError("Enter some text before publishing.")
    if action_count_today() >= settings.daily_write_cap:
        raise RuntimeError(f"Local daily write cap reached ({settings.daily_write_cap}).")
    if duplicate_recent(text):
        raise RuntimeError("Duplicate text blocked. Edit the wording before posting.")

@app.post("/post")
async def post(text: str = Form(...)):
    try:
        ensure_can_write(text)
        result = await x_api.create_post(text.strip())
        log_action("post", text.strip(), result.get("data", {}).get("id"))
        return RedirectResponse("/?ok=Post+published", status_code=303)
    except Exception as e:
        return RedirectResponse(f"/?error={quote(str(e))}", status_code=303)

def write_error(request, text, tweet_url, tweet_text, author_username, error):
    # Preserve the edited reply and its source if X rejects a write.
    try:
        source = parse_tweet_url(tweet_url)
    except ValueError:
        return RedirectResponse(f"/?error={quote(error)}", status_code=303)
    source["author_username"] = author_username or source["author_username"]
    return templates.TemplateResponse(
        "draft.html",
        ctx(request, **source, tweet_text=tweet_text, draft=text, error=error),
        status_code=400,
    )


@app.post("/quote")
async def quote_post(
    request: Request,
    tweet_id: str = Form(...),
    text: str = Form(...),
    tweet_url: str = Form(""),
    tweet_text: str = Form(""),
    author_username: str = Form(""),
):
    try:
        ensure_can_write(text)
        result = await x_api.create_quote(text.strip(), tweet_id)
        log_action("quote", text.strip(), tweet_id)
        return RedirectResponse("/?ok=Quote+published", status_code=303)
    except Exception as e:
        return write_error(request, text, tweet_url, tweet_text, author_username, str(e))


@app.post("/reply")
async def reply(
    request: Request,
    tweet_id: str = Form(...),
    text: str = Form(...),
    tweet_url: str = Form(""),
    tweet_text: str = Form(""),
    author_username: str = Form(""),
):
    try:
        ensure_can_write(text)
        result = await x_api.create_reply(text.strip(), tweet_id)
        log_action("reply", text.strip(), tweet_id)
        return RedirectResponse("/?ok=Reply+published", status_code=303)
    except Exception as e:
        # Do not retry. Keep the draft available for manual approval on X.
        msg = "API reply did not complete. Check X before trying again or replying manually. " + str(e)
        return write_error(request, text, tweet_url, tweet_text, author_username, msg)
