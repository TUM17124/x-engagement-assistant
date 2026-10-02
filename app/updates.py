"""GitHub release discovery, free email signup links, and approved signed updates."""
import asyncio
import os
import re
import time
import uuid

import httpx
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from . import database as db, preferences as prefs
from contextlib import closing
from .paths import VERSION
from .desktop_control import authorize

REPOSITORY = "TUM17124/x-engagement-assistant"
GITHUB = "https://github.com/" + REPOSITORY
RELEASE_API = "https://api.github.com/repos/" + REPOSITORY + "/releases/latest"
ASSET = "Social-Engagement-Command-Center-Setup.exe"
DOWNLOAD = GITHUB + "/releases/latest/download/" + ASSET
EMAIL_SIGNUP = "https://blogtrottr.com/?subscribe=https%3A%2F%2Fgithub.com%2F"+REPOSITORY.replace("/", "%2F")+"%2Freleases.atom"
CHECK_LOCK = asyncio.Lock()

router = APIRouter()

def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r"v?\d+\.\d+\.\d+", value):
        raise ValueError("The release version is not a stable version.")
    return tuple(int(p) for p in value.lstrip("v").split("."))

def parse_release(data):
    if not isinstance(data, dict) or data.get("draft") or data.get("prerelease"):
        raise ValueError("GitHub did not return a published stable release.")
    version = str(data.get("tag_name", "")).removeprefix("v")
    version_tuple(version)
    release_url = GITHUB + "/releases/tag/v" + version
    if data.get("html_url") != release_url:
        raise ValueError("Release details do not match this application's repository.")
    expected = GITHUB + "/releases/download/v" + version + "/"
    assets = {a.get("name"): a.get("browser_download_url") for a in data.get("assets", [])}
    if assets.get(ASSET) != expected + ASSET:
        raise ValueError("This release does not yet include the Windows installer.")
    signed = assets.get("latest.json") == expected + "latest.json" and assets.get(ASSET+".sig") == expected+ASSET+".sig"
    return {"version": version, "available": version_tuple(version)>version_tuple(VERSION),
            "notes": str(data.get("body") or "")[:12000], "published_at": data.get("published_at"),
            "release_url": release_url, "download_url": expected + ASSET, "signed": signed}

def status():
    release=db.get_setting("release_status", {})
    if release.get("version"):
        release["available"]=version_tuple(release["version"])>version_tuple(VERSION)
    return {"current_version": VERSION, "repository": GITHUB, "download_url": DOWNLOAD,
            "desktop": bool(os.getenv("XEA_DESKTOP_TOKEN")), "release": release,
            "installation": db.get_setting("update_installation", {}), "email_signup_url": EMAIL_SIGNUP,
            "settings": {"check_updates":prefs.get("check_updates")}}

async def check_release(force=False):
    async with CHECK_LOCK:
        now = time.time()
        cache = db.get_setting("release_status", {})
        if now < cache.get("retry_after", 0) or now-cache.get("attempted_at",0) < (60 if force else 6*3600):
            return status()
        cache.update(attempted_at=now)
        db.set_setting("release_status", cache)
        headers = {"Accept":"application/vnd.github+json", "User-Agent":"Social-Engagement-Command-Center/"+VERSION}
        if cache.get("etag"):
            headers["If-None-Match"] = cache["etag"]
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
                response = await client.get(RELEASE_API, headers=headers)
            if response.status_code == 304 and cache.get("version"):
                cache.update(error="", checked_at=db.now(), available=version_tuple(cache["version"])>version_tuple(VERSION))
            elif response.status_code == 404:
                cache = {"attempted_at":now, "checked_at":db.now(), "available":False,
                         "message":"No public installer release is available yet. Check again after a release is published."}
            elif response.status_code in (403,429):
                retry = max(3600, min(86400, int(response.headers.get("retry-after","3600"))))
                cache.update(error="GitHub has temporarily limited update checks. Try again later.", retry_after=now+retry)
            else:
                response.raise_for_status()
                cache = {**parse_release(response.json()), "attempted_at":now, "checked_at":db.now(),
                         "etag":response.headers.get("etag",""), "error":""}
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            cache.update(error="Could not check the official GitHub release. Check your internet connection or open GitHub releases.")
        db.set_setting("release_status", cache)
        if cache.get("available") and not cache.get("error"):
            if db.get_setting("update_notified_version") != cache["version"]:
                from .workspace import notify
                notify("App update "+cache["version"]+" is available. Open Settings > Updates.")
                db.set_setting("update_notified_version",cache["version"])
        return status()

@router.get("/api/updates")
def read(): return status()

@router.post("/api/updates/check")
async def check(): return await check_release(force=True)

class InstallRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    version:str
    confirmed:bool=False

def busy():
    from .terminal_routes import TASKS
    return bool(TASKS or db.one("SELECT id FROM drafts WHERE status='sending'") or
                db.one("SELECT id FROM scheduled_posts WHERE status='sending'"))

@router.post("/api/updates/install")
async def install(data:InstallRequest):
    if not os.getenv("XEA_DESKTOP_TOKEN"):
        raise ValueError("Open the installed desktop app to update, or download the Windows installer from GitHub.")
    release=db.get_setting("release_status",{})
    if not data.confirmed or not release.get("available") or not release.get("signed") or release.get("error") or data.version!=release.get("version"):
        raise ValueError("Check for updates and explicitly confirm the displayed signed release first.")
    old=db.get_setting("update_installation",{})
    if old.get("state") in {"queued","downloading","installing"}:
        raise ValueError("An update is already running. Wait for its result.")
    if busy():
        raise ValueError("Wait for current terminal or publishing work to finish before updating.")
    job={"id":str(uuid.uuid4()),"version":data.version,"state":"queued","message":"Waiting for the desktop updater.","created_at":time.time()}
    db.set_setting("update_installation",job)
    return job

@router.get("/desktop/update-request")
async def update_request(request:Request):
    authorize(request)
    job=db.get_setting("update_installation",{})
    if job.get("state")=="queued":
        job.update(state="downloading",message="Checking the signed release and preparing download.")
        db.set_setting("update_installation",job)
        return job
    return {}

class UpdateProgress(BaseModel):
    model_config=ConfigDict(extra="forbid")
    id:str
    state:str
    message:str=Field(max_length=600)
    downloaded:int=Field(default=0,ge=0)
    total:int|None=Field(default=None,ge=0)

@router.post("/desktop/update-progress")
async def update_progress(request:Request,data:UpdateProgress):
    authorize(request)
    if data.state not in {"downloading","installing","failed"}:
        raise ValueError("Invalid updater state.")
    job=db.get_setting("update_installation",{})
    if job.get("id")!=data.id or job.get("state") not in {"downloading","installing"}:
        raise ValueError("This updater request is no longer active.")
    if job.get("state")=="installing" and data.state=="downloading":
        return {"ok":True}
    job.update(data.model_dump())
    db.set_setting("update_installation",job)
    return {"ok":True}

@router.post("/desktop/prepare-update")
async def prepare_update(request:Request):
    authorize(request)
    if busy():
        raise ValueError("An operation started during the download. Finish it, then try updating again.")
    job=db.get_setting("update_installation",{})
    if job.get("state")!="installing":
        raise ValueError("No verified update is ready.")
    # Private SQLite backup before a version migration; never export credentials.
    from .paths import data_dir
    import sqlite3
    folder=data_dir()/"backups";folder.mkdir(parents=True,exist_ok=True)
    with db.conn() as source, closing(sqlite3.connect(folder/("before-update-"+VERSION+".sqlite3"))) as target:
        source.backup(target)
    from .desktop_control import shutdown_handler
    if shutdown_handler: shutdown_handler()
    return {"ok":True}

def recover_updates():
    job=db.get_setting("update_installation",{})
    if job.get("state") in {"queued","downloading","installing"}:
        done=job.get("version")==VERSION
        job.update(state="completed" if done else "interrupted",
                   message="App update completed." if done else "The update was interrupted. Check for updates before trying again.")
        db.set_setting("update_installation",job)

async def loop():
    recover_updates()
    while True:
        if prefs.get("check_updates"):
            try: await check_release()
            except Exception: pass
        await asyncio.sleep(300)
