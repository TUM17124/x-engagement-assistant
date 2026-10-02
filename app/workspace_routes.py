import json
import re
from datetime import datetime,timezone,timedelta
from urllib.parse import urlencode
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel, Field
from . import database as db, preferences as prefs, workspace as ws, discovery
from .providers import provider
from .storage import action_count_today,load_tokens

router=APIRouter(prefix="/api")

class ImportInput(BaseModel):
    tweet_url: str = Field(max_length=2048)
    text: str = Field(default="",max_length=30000)
    username: str = Field(default="",max_length=16)
    fetch: bool = False

class DraftInput(BaseModel):
    kind: str
    text: str = Field(max_length=20000)
    feed_id: str | None = None
    generated_text: str = Field(default="",max_length=20000)

class ReplyInput(BaseModel):
    feed_id: str
    style: str = ""
    draft_id: int | None = None

class AIInput(BaseModel):
    text: str = Field(min_length=1,max_length=20000)
    operation: str = "Generate post"
    kind: str = "original"

class ScheduleInput(BaseModel):
    due_at: str
    timezone: str

class WatchInput(BaseModel):
    username: str = Field(max_length=16)
    enabled: bool = True
    priority: str = "Normal"
    topics: str = Field(default="",max_length=500)
    ai_drafting: bool = False
    notifications: bool = False

class TopicInput(BaseModel):
    name: str = Field(min_length=1,max_length=100)
    keywords: str = Field(min_length=1,max_length=1000)
    excluded: str = Field(default="",max_length=500)
    languages: str = Field(default="en",max_length=100)
    enabled: bool = True
    priority: str = "Normal"
    query: str = Field(default="",max_length=2000)

@router.get("/dashboard")
def dashboard():
    counts={r["status"]:r["n"] for r in db.rows("SELECT status,COUNT(*) n FROM drafts GROUP BY status")}
    published=db.rows("SELECT action,COUNT(*) n FROM activity WHERE status='published' GROUP BY action")
    approved=db.one("SELECT COUNT(DISTINCT draft_id) n FROM activity WHERE action='approved'")["n"]
    generated=db.one("SELECT COUNT(*) n FROM drafts WHERE generated_text<>''")["n"]
    accepted=db.one("SELECT COUNT(DISTINCT a.draft_id) n FROM activity a JOIN drafts d ON a.draft_id=d.id WHERE a.action='approved' AND d.generated_text<>''")["n"]
    return {"profile":db.get_setting("x_profile"),"x_connected":bool(load_tokens()),
        "x_health":db.get_setting("x_health"),"ai_health":db.get_setting("ai_health"),"provider":prefs.get("ai_provider"),"model":prefs.get("chatgpt_model") if prefs.get("ai_provider")=="chatgpt" else prefs.get("ai_model"),
        "scheduler":db.get_setting("scheduler_state","Stopped"),"today_writes":action_count_today(),
        "drafts":counts,"published":published,"approved":approved,"generated":generated,
        "acceptance_rate":round(accepted/generated*100,1) if generated else None,
        "skipped":db.one("SELECT COUNT(*) n FROM activity WHERE action='reply_skipped'")["n"],
        "scheduled":db.one("SELECT COUNT(*) n FROM scheduled_posts WHERE status='pending'")["n"],
        "watchlist_updates":db.one("SELECT COUNT(*) n FROM feed_items WHERE source='Watchlist' AND substr(imported_at,1,10)=?",(db.now()[:10],))["n"],
        "topics":db.rows("SELECT topic,COUNT(*) n FROM activity WHERE status='published' AND topic<>'' GROUP BY topic ORDER BY n DESC LIMIT 5"),
        "accounts":db.rows("SELECT target_account,COUNT(*) n FROM activity WHERE status='published' AND target_account<>'' GROUP BY target_account ORDER BY n DESC LIMIT 5"),
        "discovery_error":db.get_setting("discovery_blocked") or "",
        "recent":db.rows("SELECT * FROM activity ORDER BY id DESC LIMIT 8")}

@router.get("/feed")
def feed(source: str="", saved: bool=False):
    sql="""SELECT * FROM feed_items WHERE ignored=0 AND lower(username) NOT IN (SELECT username FROM muted_accounts)
      AND lower(topic) NOT IN (SELECT topic FROM muted_topics)"""
    args=[]
    if source:
        sql+=" AND source=?";args.append(source)
    if saved:
        sql+=" AND saved=1"
    return db.rows(sql+" ORDER BY imported_at DESC LIMIT 200",args)

@router.post("/feed/import")
async def import_feed(data: ImportInput):
    parsed=ws.parse_tweet_url(data.tweet_url)
    if not data.text.strip() and data.fetch:
        await discovery.fetch_post(parsed["tweet_id"])
        item=db.one("SELECT * FROM feed_items WHERE id=?",(parsed["tweet_id"],))
        if item:
            return item
    return ws.import_post(data.tweet_url,data.text,data.username)

@router.post("/feed/{feed_id}/{action}")
def feed_action(feed_id: str,action: str):
    if action not in {"save","unsave","ignore"}:
        raise ValueError("Unknown feed action.")
    if action=="ignore":
        db.execute("UPDATE feed_items SET ignored=1 WHERE id=?",(feed_id,))
    else:
        db.execute("UPDATE feed_items SET saved=? WHERE id=?",(int(action=="save"),feed_id))
    return {"ok":True}

@router.get("/drafts")
def drafts(kind: str=""):
    sql="SELECT d.*,f.username,f.text source_text FROM drafts d LEFT JOIN feed_items f ON d.feed_id=f.id"
    args=[]
    if kind:
        sql+=" WHERE d.kind=?";args.append(kind)
    return db.rows(sql+" ORDER BY d.score DESC,d.id DESC LIMIT 200",args)

@router.post("/drafts")
def create_draft(data: DraftInput):
    return ws.save_draft(data.kind,data.text,data.feed_id,generated=data.generated_text)

@router.put("/drafts/{draft_id}")
def edit_draft(draft_id: int,data: DraftInput):
    return ws.save_draft(data.kind,data.text,data.feed_id,generated=data.generated_text,draft_id=draft_id)

@router.post("/generate/reply")
async def generate_reply(data: ReplyInput):
    return await ws.generate_reply(data.feed_id,data.style,data.draft_id)

@router.post("/generate/compose")
async def generate_compose(data: AIInput):
    operations={"Generate post","Rewrite","Shorten","Make more natural","Make more technical",
                "Make more casual","Generate hook","Generate 3 alternatives","Check repetitive wording"}
    if data.operation not in operations:
        raise ValueError("Choose an available AI tool.")
    if data.operation=="Check repetitive wording":
        recent=db.rows("SELECT text FROM actions ORDER BY id DESC LIMIT 20")
        return {"text":await ws.ai_call(lambda:provider().rewrite(data.text,
            "Give brief feedback only on repetitive wording versus these previous posts: "+json.dumps(recent)))}
    result=await ws.ai_call(lambda:provider().generate_post(data.text,data.kind) if data.operation=="Generate post"
                            else provider().rewrite(data.text,data.operation))
    return {"text":result}

@router.post("/drafts/{draft_id}/approve")
def approve(draft_id: int):
    return ws.approve(draft_id)

@router.post("/drafts/{draft_id}/publish")
async def publish(draft_id: int):
    return await ws.publish(draft_id)

@router.post("/drafts/{draft_id}/manual")
def manual(draft_id: int):
    draft=ws.require_approved(draft_id)
    if draft["kind"]!="reply":
        raise ValueError("The manual reply action is for reply drafts.")
    ws.activity("manual_composer_opened",draft,status="opened",channel="manual")
    return {"url":"https://x.com/intent/tweet?"+urlencode({"in_reply_to":draft["feed_id"],"text":draft["text"]}),
            "note":"Opening the composer does not confirm a published reply."}

@router.post("/drafts/{draft_id}/skip")
def skip(draft_id: int):
    draft=ws.get_draft(draft_id)
    if draft["status"] in {"published","sending","uncertain","partial"}:
        raise ValueError("This draft cannot be skipped.")
    db.execute("UPDATE drafts SET status='skipped' WHERE id=?",(draft_id,))
    db.execute("DELETE FROM approved_content WHERE draft_id=?",(draft_id,))
    db.execute("UPDATE scheduled_posts SET status='cancelled' WHERE draft_id=?",(draft_id,))
    ws.activity("reply_skipped" if draft["kind"]=="reply" else "skipped",draft,status="skipped")
    return {"ok":True}

@router.post("/mute/{kind}")
def mute(kind: str,data: dict):
    value=str(data.get("value","")).strip().lower()
    if not value or len(value)>100:
        raise ValueError("Choose an author or topic to mute.")
    if kind=="author":
        db.execute("INSERT OR IGNORE INTO muted_accounts VALUES(?)",(value,))
    elif kind=="topic":
        db.execute("INSERT OR IGNORE INTO muted_topics VALUES(?)",(value,))
    else:
        raise ValueError("Unknown mute type.")
    return {"ok":True}

@router.get("/mutes")
def mutes():
    return {"authors":db.rows("SELECT * FROM muted_accounts"),"topics":db.rows("SELECT * FROM muted_topics")}

@router.post("/unmute/{kind}")
def unmute(kind: str,data: dict):
    table,column=("muted_accounts","username") if kind=="author" else ("muted_topics","topic")
    db.execute(f"DELETE FROM {table} WHERE {column}=?",(str(data.get("value","")).lower(),))
    return {"ok":True}

@router.get("/schedule")
def schedules():
    return db.rows("SELECT s.*,d.text,d.platform,d.status draft_status FROM scheduled_posts s JOIN drafts d ON s.draft_id=d.id ORDER BY s.due_at")

@router.post("/drafts/{draft_id}/schedule")
def schedule(draft_id: int,data: ScheduleInput):
    return ws.schedule(draft_id,data.due_at,data.timezone)

@router.delete("/schedule/{schedule_id}")
def cancel_schedule(schedule_id: int):
    item=db.one("SELECT * FROM scheduled_posts WHERE id=?",(schedule_id,))
    if not item or item["status"]=="sending":
        raise ValueError("Schedule unavailable or currently publishing.")
    db.execute("UPDATE scheduled_posts SET status='cancelled' WHERE id=?",(schedule_id,))
    db.execute("UPDATE drafts SET status='approved' WHERE id=? AND status='scheduled'",(item["draft_id"],))
    return {"ok":True}

@router.get("/watchlist")
def watchlist():
    return db.rows("SELECT * FROM watched_accounts ORDER BY id DESC")

def validate_watch(data):
    username=data.username.strip().lstrip("@")
    if not re.fullmatch(r"[A-Za-z0-9_]{1,15}",username):
        raise ValueError("Enter an X username using letters, numbers, and underscores.")
    if data.priority not in {"Low","Normal","High"}:
        raise ValueError("Choose a priority.")
    return username

@router.post("/watchlist")
def add_watch(data: WatchInput):
    username=validate_watch(data)
    if db.one("SELECT 1 FROM watched_accounts WHERE lower(username)=?",(username.lower(),)):
        raise ValueError("That account is already on your watchlist.")
    return {"id":db.execute("INSERT INTO watched_accounts(username,enabled,priority,topics,ai_drafting,notifications) VALUES(?,?,?,?,?,?)",
        (username,data.enabled,data.priority,data.topics,data.ai_drafting,data.notifications))}

@router.put("/watchlist/{item_id}")
def edit_watch(item_id: int,data: WatchInput):
    username=validate_watch(data)
    db.execute("UPDATE watched_accounts SET username=?,enabled=?,priority=?,topics=?,ai_drafting=?,notifications=? WHERE id=?",
               (username,data.enabled,data.priority,data.topics,data.ai_drafting,data.notifications,item_id))
    return {"ok":True}

@router.delete("/watchlist/{item_id}")
def delete_watch(item_id: int):
    db.execute("DELETE FROM watched_accounts WHERE id=?",(item_id,))
    return {"ok":True}

@router.post("/watchlist/{item_id}/refresh")
async def refresh_watch(item_id: int):
    return {"items":await discovery.poll_account(item_id)}

@router.get("/topics")
def topics():
    return [{**t,"search_url":discovery.web_search(t["query"] or discovery.query_for(t))} for t in db.rows("SELECT * FROM tracked_topics ORDER BY id DESC")]

def validate_topic(data):
    if data.priority not in {"Low","Normal","High"}:
        raise ValueError("Choose a priority.")
    return data.query.strip() or discovery.query_for(data.model_dump())

@router.post("/topics")
def add_topic(data: TopicInput):
    query=validate_topic(data)
    return {"id":db.execute("INSERT INTO tracked_topics(name,keywords,excluded,languages,enabled,priority,query) VALUES(?,?,?,?,?,?,?)",
        (data.name,data.keywords,data.excluded,data.languages,data.enabled,data.priority,query))}

@router.put("/topics/{item_id}")
def edit_topic(item_id: int,data: TopicInput):
    query=validate_topic(data)
    db.execute("UPDATE tracked_topics SET name=?,keywords=?,excluded=?,languages=?,enabled=?,priority=?,query=? WHERE id=?",
        (data.name,data.keywords,data.excluded,data.languages,data.enabled,data.priority,query,item_id))
    return {"ok":True}

@router.delete("/topics/{item_id}")
def delete_topic(item_id: int):
    db.execute("DELETE FROM tracked_topics WHERE id=?",(item_id,))
    return {"ok":True}

@router.post("/topics/{item_id}/refresh")
async def refresh_topic(item_id: int):
    return {"items":await discovery.poll_topic(item_id)}

@router.post("/topics/suggest/query")
async def suggest_query(data: TopicInput):
    result=await ws.ai_call(lambda:provider().rewrite(json.dumps(data.model_dump()),
       "Return ONLY an X search query matching these keywords, exclusions, and languages. Use official public search syntax, no explanation."))
    return {"query":result[:2000]}

@router.post("/discovery/resume")
def resume_discovery():
    db.set_setting("discovery_blocked","")
    # Do not clear rate-limit backoff; a manual resume must respect the provider's reset.
    prefs.save({"monitoring":True})
    return {"ok":True}

@router.get("/history")
def history(action: str="",status: str="",channel: str=""):
    sql="SELECT * FROM activity WHERE 1=1";args=[]
    for key,value in (("action",action),("status",status),("channel",channel)):
        if value:
            sql+=" AND "+key+"=?";args.append(value)
    return db.rows(sql+" ORDER BY id DESC LIMIT 500",args)

@router.get("/notifications")
def notifications():
    return db.rows("SELECT * FROM notifications ORDER BY id DESC LIMIT 20")

@router.get("/export/{kind}")
def export(kind: str):
    if kind=="settings":
        content=prefs.all_settings()
    elif kind=="drafts":
        content=db.rows("SELECT * FROM drafts")
    elif kind=="history":
        content=db.rows("SELECT * FROM activity")
    elif kind=="database":
        from .backup import backup_bytes
        return Response(backup_bytes(),media_type="application/vnd.sqlite3",
                        headers={"Content-Disposition":'attachment; filename="xea-backup.sqlite3"'})
    else:
        raise HTTPException(404)
    return Response(json.dumps(content,indent=2),media_type="application/json",
                    headers={"Content-Disposition":f'attachment; filename="xea-{kind}.json"'})

@router.post("/restore")
async def restore(file: UploadFile=File(...)):
    from .backup import restore_bytes
    data=await file.read(20*1024*1024+1)
    if len(data)>20*1024*1024:
        raise ValueError("Maximum backup size is 20 MB.")
    async with ws.WRITE_LOCK:
        restore_bytes(data)
    return {"ok":True,"note":"Workspace restored. Restored drafts need approval; schedules are cancelled for review. Credentials were not imported."}

@router.post("/import/settings")
def import_settings(data: dict):
    prefs.save(data)
    return {"ok":True}

@router.post("/import/legacy")
async def import_legacy(file: UploadFile=File(...)):
    from .legacy import import_legacy
    data=await file.read(20*1024*1024+1)
    if len(data)>20*1024*1024:
        raise ValueError("Maximum legacy database size is 20 MB.")
    async with ws.WRITE_LOCK:
        return import_legacy(data)
