"""Engagement domain: drafts are editable; approval binds exact content."""
import asyncio
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from . import database as db, preferences as prefs, x_api
from .storage import log_action, duplicate_recent, action_count_today
from .providers import provider
from .post_urls import parse_tweet_url

WRITE_LOCK = asyncio.Lock()
AI_LOCK = asyncio.Lock()
KINDS = {"reply", "comment", "original", "quote", "thread"}
STYLES = {"", "Shorter", "More casual", "More technical", "More humorous", "Disagree politely",
          "Ask a question", "Mention my product naturally", "Do NOT mention my product", "Longer", "More professional", "Humanize"}

def content_hash(draft):
    value={k:draft.get(k) for k in ("kind","feed_id","text","platform","account_id","media_ids")}
    value["media"]=[db.one("SELECT id,alt_text FROM media WHERE id=?",(id,)) for id in json.loads(draft.get("media_ids") or "[]")]
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

def get_draft(draft_id):
    value = db.one("SELECT d.*, f.username, f.text source_text, f.id target_id FROM drafts d LEFT JOIN feed_items f ON d.feed_id=f.id WHERE d.id=?", (draft_id,))
    if not value:
        raise ValueError("Draft not found.")
    return value

def activity(action, draft=None, status="success", channel="local", post_id=None, error=""):
    draft = draft or {}
    db.execute("""INSERT INTO activity(action,timestamp,draft_id,post_id,target_account,generated_text,
      final_text,provider,model,channel,status,error,topic,platform) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
      (action,db.now(),draft.get("id"),post_id,draft.get("username") or "",draft.get("generated_text",""),
       draft.get("text",""),draft.get("provider",""),draft.get("model",""),channel,status,error,draft.get("topic",""),draft.get("platform","x")))

def notify(title):
    if prefs.get("notifications"):
        db.execute("INSERT INTO notifications(title,created_at) VALUES(?,?)",(title,db.now()))

def import_post(url, text="", username="", source="manual", **extra):
    parsed = parse_tweet_url(url)
    username = username.strip().lstrip("@") or parsed["author_username"]
    if not re.fullmatch(r"[A-Za-z0-9_]{1,15}",username):
        raise ValueError("Enter a valid X username.")
    if not text.strip():
        raise ValueError("Paste the post text, or use Fetch with X API if you have read access.")
    db.execute("""INSERT INTO feed_items(id,username,text,imported_at,source,display_name,avatar,posted_at,metrics,topic)
      VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING""",
      (parsed["tweet_id"],username,text.strip(),db.now(),source,extra.get("display_name",""),
       extra.get("avatar",""),extra.get("posted_at"),json.dumps(extra.get("metrics",{})),extra.get("topic","")))
    return db.one("SELECT * FROM feed_items WHERE id=?",(parsed["tweet_id"],))

def save_draft(kind, text, feed_id=None, generated="", reason="", score=0, topic="", draft_id=None, platform="x", media_ids=None):
    if kind not in KINDS:
        raise ValueError("Choose an original post, reply, quote, or thread.")
    if not isinstance(text,str) or len(text)>20000:
        raise ValueError("Draft is too long.")
    if kind in {"reply","quote","comment"} and not db.one("SELECT id FROM feed_items WHERE id=?",(feed_id,)):
        raise ValueError("Select or import the original post first.")
    if platform != "x":
        from .social.catalog import definition
        definition(platform)
        if kind in {"thread","quote"}:raise ValueError("Use original posts or responses for this platform. Threads and quotes remain available in X Compose.")
    if media_ids is not None:
        if len(media_ids)>4 or any(not db.one("SELECT id FROM media WHERE id=?",(id,)) for id in media_ids):
            raise ValueError("Choose up to four existing media files.")
    if draft_id:
        current = get_draft(draft_id)
        platform = current.get("platform","x") if platform=="x" else platform
        if current["status"] in {"sending","published","uncertain","partial"}:
            raise ValueError("This draft has already been sent or needs reconciliation. Create a new draft.")
        with db.conn() as c:
            c.execute("UPDATE drafts SET kind=?,text=?,feed_id=?,status='draft',updated_at=? WHERE id=?",
                      (kind,text,feed_id,db.now(),draft_id))
            if generated:
                c.execute("UPDATE drafts SET generated_text=?,provider=?,model=? WHERE id=?",(generated,prefs.get("ai_provider"),prefs.get("ai_model"),draft_id))
            c.execute("DELETE FROM approved_content WHERE draft_id=?",(draft_id,))
            c.execute("UPDATE scheduled_posts SET status='cancelled' WHERE draft_id=?",(draft_id,))
        if media_ids is not None:
            db.execute("UPDATE drafts SET media_ids=? WHERE id=?",(json.dumps(media_ids),draft_id))
        db.execute("UPDATE drafts SET platform=? WHERE id=?",(platform,draft_id))
        return get_draft(draft_id)
    draft_id = db.execute("""INSERT INTO drafts(kind,text,feed_id,generated_text,reason,score,topic,provider,model,created_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?)""",(kind,text,feed_id,generated,reason,score,topic,
      prefs.get("ai_provider") if generated else "",prefs.get("ai_model") if generated else "",db.now(),db.now()))
    db.execute("UPDATE drafts SET platform=?,media_ids=? WHERE id=?",(platform,json.dumps(media_ids or []),draft_id))
    return get_draft(draft_id)

async def ai_call(operation):
    async with AI_LOCK:
        paused=db.get_setting("ai_pause",{})
        if paused.get("blocked") or paused.get("until","")>db.now():
            raise ValueError(paused.get("message","AI is paused. Test the connection after fixing access."))
        with db.conn() as c:
            used = c.execute("SELECT COUNT(*) FROM ai_usage WHERE substr(created_at,1,10)=?",(db.now()[:10],)).fetchone()[0]
            if used >= prefs.get("daily_ai_limit"):
                raise ValueError("Daily AI draft limit reached. Review existing drafts or adjust Safety Limits.")
            c.execute("INSERT INTO ai_usage(created_at) VALUES(?)",(db.now(),))
        from .errors import ServiceError
        paused=db.get_setting("ai_pause",{})
        if paused.get("blocked") or paused.get("until","")>db.now():
            raise ValueError(paused.get("message","AI is paused. Test the connection after fixing access."))
        try:
            return await operation()
        except ServiceError as error:
            state={"message":str(error)}
            if error.status in {401,402,403}:state["blocked"]=True
            if error.status==429:state["until"]=(datetime.now(timezone.utc)+timedelta(seconds=max(error.retry_after,60))).isoformat()
            db.set_setting("ai_pause",state)
            raise

async def generate_reply(feed_id, style="", draft_id=None):
    if style not in STYLES:
        raise ValueError("Unknown reply style.")
    feed = db.one("SELECT * FROM feed_items WHERE id=?",(feed_id,))
    if not feed or feed["ignored"]:
        raise ValueError("Post is unavailable or ignored.")
    if db.one("SELECT 1 FROM muted_accounts WHERE username=?",(feed["username"].lower(),)) or db.one("SELECT 1 FROM muted_topics WHERE topic=?",(feed["topic"].lower(),)):
        raise ValueError("This author or topic is muted.")
    source = {"text":feed["text"],"username":feed["username"],"topic":feed["topic"]}
    if draft_id:
        current = get_draft(draft_id)
        if current["feed_id"] != feed_id or current["status"] in {"sending","published","uncertain","partial"}:
            raise ValueError("Choose an editable draft for this source.")
        if style:
            source["current_draft"] = current["text"]
    source["platform"]=feed.get("platform","x")
    result = await ai_call(lambda: provider().generate_reply(source,style,rank=True))
    clean = re.sub(r"^\`\`\`(?:json)?\s*|\s*\`\`\`$", "", result.strip())
    try:
        data = json.loads(clean)
        text = str(data["reply"]).strip()
        reason = str(data.get("reason","Relevant to your interests"))[:1000]
        score = max(0,min(100,int(data.get("score",50))))
        topic = str(data.get("topic",feed["topic"]))[:100]
    except (ValueError,KeyError,TypeError):
        text,reason,score,topic = result.strip(),"Drafted from the specific post you selected.",50,feed["topic"]
    if text.upper().strip('".') == "SKIP":
        db.execute("UPDATE feed_items SET ignored=1 WHERE id=?",(feed_id,))
        activity("reply_skipped",{"username":feed["username"],"topic":topic},status="skipped")
        return {"skipped":True}
    if draft_id:
        draft = get_draft(draft_id)
        if draft["feed_id"] != feed_id:
            raise ValueError("Draft does not match this source.")
        updated = save_draft("reply",text,feed_id,draft_id=draft_id)
        db.execute("UPDATE drafts SET generated_text=?,provider=?,model=?,reason=?,score=?,topic=? WHERE id=?",
                   (text,prefs.get("ai_provider"),prefs.get("ai_model"),reason,score,topic,draft_id))
        return get_draft(draft_id)
    draft = save_draft("reply",text,feed_id,text,reason,score,topic)
    notify("A new reply draft is ready for review.")
    return draft

def parts(draft):
    values = [p.strip() for p in draft["text"].split("\n---\n")] if draft["kind"] == "thread" else [draft["text"].strip()]
    from .social.catalog import definition
    limit=definition(draft.get("platform","x"))["limit"]
    if not 1 <= len(values) <= 10 or any(not p or len(p)>limit for p in values):
        raise ValueError(f"Each post must contain 1-{limit} characters. X threads support up to 10 posts separated by a line containing ---.")
    return values

def safety(draft):
    texts = parts(draft)
    count = len(texts)
    if action_count_today()+count > prefs.get("daily_write_cap"):
        raise ValueError("Local daily write cap reached.")
    hourly = db.one("SELECT COUNT(*) n FROM actions WHERE created_at>=?",((datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),))["n"]
    if hourly+count > prefs.get("hourly_write_limit"):
        raise ValueError("Hourly write limit reached. Please come back later.")
    action = "reply" if draft["kind"] in {"reply","comment"} else "post"
    daily = db.one("SELECT COUNT(*) n FROM actions WHERE substr(created_at,1,10)=? AND "+
        ("action_type IN ('reply','comment')" if action=="reply" else "action_type IN ('post','quote')"),(db.now()[:10],))["n"]
    if daily+count > prefs.get("daily_reply_limit" if action=="reply" else "daily_post_limit"):
        raise ValueError("Daily approved reply or original-post limit reached.")
    previous = db.rows("SELECT text FROM actions ORDER BY id DESC LIMIT 100")
    seen = []
    for text in texts:
        if duplicate_recent(text) or text in seen:
            raise ValueError("Duplicate content blocked. Change the wording before approving.")
        if any(SequenceMatcher(None,text.casefold(),p.casefold()).ratio() >= .9 for p in seen+[x["text"] for x in previous if x["text"]]):
            raise ValueError("This content is very similar to a recent post. Add a more specific, useful response.")
        seen.append(text)
    if draft["kind"] in {"reply","comment"}:
        n = db.one("SELECT COUNT(*) n FROM activity WHERE action IN ('reply','comment') AND status='published' AND target_account=? AND substr(timestamp,1,10)=?",
                   (draft.get("username",""),db.now()[:10]))["n"]
        if n >= prefs.get("same_account_limit"):
            raise ValueError("You have already replied to this account several times today. Try a different conversation.")
    return texts

def approve(draft_id):
    draft = get_draft(draft_id)
    if draft["status"] in {"published","sending","uncertain","partial"}:
        raise ValueError("This draft cannot be approved again.")
    safety(draft)
    if draft.get("platform","x") != "x":
        from .social.registry import provider as social_provider
        account=social_provider(draft["platform"]).account.get("account_id","")
        db.execute("UPDATE drafts SET account_id=? WHERE id=?",(account,draft_id))
        draft=get_draft(draft_id)
    with db.conn() as c:
        c.execute("INSERT INTO approved_content VALUES(?,?,?) ON CONFLICT(draft_id) DO UPDATE SET content_hash=excluded.content_hash,approved_at=excluded.approved_at",
                  (draft_id,content_hash(draft),db.now()))
        c.execute("UPDATE drafts SET status='approved',updated_at=? WHERE id=?",(db.now(),draft_id))
    activity("approved",draft,status="approved")
    return get_draft(draft_id)

def require_approved(draft_id):
    draft = get_draft(draft_id)
    approval = db.one("SELECT * FROM approved_content WHERE draft_id=?",(draft_id,))
    if not approval or approval["content_hash"] != content_hash(draft) or draft["status"] not in {"approved","scheduled"}:
        raise ValueError("Review and approve this exact content first. Editing clears approval.")
    return draft

async def publish(draft_id, scheduled=False):
    async with WRITE_LOCK:
        draft = require_approved(draft_id)
        if scheduled and draft["kind"] != "original":
            raise ValueError("Only explicitly approved original posts can publish on a schedule.")
        texts = safety(draft)
        with db.conn() as c:
            changed = c.execute("UPDATE drafts SET status='sending' WHERE id=? AND status IN ('approved','scheduled')",(draft_id,)).rowcount
            if not changed:
                raise ValueError("This draft is already being processed.")
        ids = []
        try:
            for text in texts:
                if draft.get("platform","x") != "x":
                    from .social.publishing import send_approved
                    post_id = await send_approved(draft,text)
                    result={"data":{"id":post_id}}
                elif json.loads(draft.get("media_ids") or "[]"):
                    raise ValueError("X media publishing uses manual handoff in this release.")
                elif draft["kind"]=="reply":
                    result = await x_api.create_reply(text,draft["feed_id"])
                elif draft["kind"]=="quote":
                    result = await x_api.create_quote(text,draft["feed_id"])
                elif ids:
                    result = await x_api.create_reply(text,ids[-1])
                else:
                    result = await x_api.create_post(text)
                post_id = result.get("data",{}).get("id")
                if not post_id:
                    raise RuntimeError("X returned no post ID. Check your profile before trying again.")
                ids.append(post_id)
                action = {"original":"post","thread":"post"}.get(draft["kind"],draft["kind"])
                log_action(action,text,post_id,draft.get('platform','x'))
                activity(action,{**draft,"text":text},status="published",channel="API",post_id=post_id)
        except Exception as error:
            from .errors import ServiceError
            state = "partial" if ids else ("failed" if isinstance(error,ServiceError) and error.status in {401,402,403,429} else "uncertain")
            db.execute("UPDATE drafts SET status=? WHERE id=?",(state,draft_id))
            message = str(error) if isinstance(error,(ServiceError,ValueError)) else "Publishing could not be confirmed. Check X before trying again."
            activity(draft["kind"],draft,status=state,channel="API",error=message)
            raise ValueError(message) from None
        db.execute("UPDATE drafts SET status='published' WHERE id=?",(draft_id,))
        db.execute("UPDATE scheduled_posts SET status='published' WHERE draft_id=?",(draft_id,))
        for media_id in json.loads(draft.get("media_ids") or "[]"):
            db.execute("INSERT INTO media_usage(media_id,draft_id,used_at) VALUES(?,?,?)",(media_id,draft_id,db.now()))
        return {"published":True,"post_ids":ids}

def schedule(draft_id, due_at, timezone_name):
    from zoneinfo import ZoneInfo
    draft = require_approved(draft_id)
    if draft["kind"] != "original":
        raise ValueError("Scheduling is available for approved original posts only. Replies remain manual approval actions.")
    due = datetime.fromisoformat(due_at.replace("Z","+00:00"))
    if due.tzinfo is None or due <= datetime.now(timezone.utc):
        raise ValueError("Choose a future time with a timezone.")
    try:
        ZoneInfo(timezone_name)
    except (KeyError,ValueError):
        raise ValueError("Choose a valid local timezone.") from None
    db.execute("""INSERT INTO scheduled_posts(draft_id,content_hash,due_at,timezone,status) VALUES(?,?,?,?,'pending')
     ON CONFLICT(draft_id) DO UPDATE SET content_hash=excluded.content_hash,due_at=excluded.due_at,
     timezone=excluded.timezone,status='pending',error='',notified=0""",
     (draft_id,content_hash(draft),due.astimezone(timezone.utc).isoformat(),timezone_name))
    db.execute("UPDATE drafts SET status='scheduled' WHERE id=?",(draft_id,))
    activity("scheduled",draft,status="scheduled")
    return {"scheduled":True}
