"""Unified content normalization, bounded listening, and local trend evidence."""
import json
import re
import uuid
from datetime import datetime,timedelta,timezone
from urllib.parse import urlsplit,parse_qs,urlencode
from difflib import SequenceMatcher
from .. import database as db,preferences as prefs,workspace as ws
from .catalog import CATALOG,definition
from .registry import provider

DOMAINS={"x":["x.com","twitter.com"],"facebook":["facebook.com","fb.watch"],"instagram":["instagram.com"],
 "linkedin":["linkedin.com"],"tiktok":["tiktok.com"],"youtube":["youtube.com","youtu.be"],"threads":["threads.net","threads.com"]}

def safe_url(platform,url):
    definition(platform)
    if not url:return CATALOG[platform]["home"]
    p=urlsplit(url.strip())
    if p.scheme!="https" or p.username or p.password or not any(p.hostname==h or (p.hostname or "").endswith("."+h) for h in DOMAINS[platform]):
        raise ValueError("Use an HTTPS link from the selected social platform.")
    return url.strip()

def ingest(item,source="API",topic=""):
    platform=item["platform"];definition(platform)
    external=str(item.get("external_id",""))
    identifier=external if platform=="x" and external.isdigit() else platform+":"+(external or uuid.uuid4().hex)
    text=str(item.get("text","")).strip()
    if not text: return None
    url=safe_url(platform,item.get("url",""))
    db.execute("""INSERT INTO feed_items(id,username,text,imported_at,source,platform,external_id,url,content_kind,
      display_name,avatar,posted_at,metrics,topic,media_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(id) DO NOTHING""",(identifier,str(item.get("username","Unknown"))[:150],text[:30000],db.now(),source,platform,external,url,
      item.get("content_kind","post"),str(item.get("display_name",""))[:150],str(item.get("avatar",""))[:2048],item.get("posted_at"),
      json.dumps(item.get("metrics",{})),topic,json.dumps(item.get("media",[]))))
    return db.one("SELECT * FROM feed_items WHERE id=?",(identifier,))

def manual_import(platform,text,url="",author="",kind="post"):
    if not text.strip():raise ValueError("Paste the original text. API access is not required.")
    if platform=="x" and url:
        parsed=ws.parse_tweet_url(url)
        return ingest({"platform":"x","external_id":parsed["tweet_id"],"url":parsed["tweet_url"],"username":author or parsed["author_username"],"text":text,"content_kind":kind},"manual")
    return ingest({"platform":platform,"url":safe_url(platform,url),"username":author or "Imported author","text":text,"content_kind":kind},"manual")

def quality(text,source=""):
    flags=[]
    banned=["absolutely!","great point!","couldn't agree more","game changer","this is the future","leverage synergies","in today's fast-paced"]
    low=text.casefold()
    if any(p in low for p in banned):flags.append("Generic enthusiasm or corporate wording")
    if sum(ord(c)>=0x1f300 for c in text)>3:flags.append("Many emoji; consider removing some")
    recent=[r["text"] for r in db.rows("SELECT text FROM actions ORDER BY id DESC LIMIT 50")]
    opening=" ".join(low.split()[:5])
    if opening and any(" ".join(t.casefold().split()[:5])==opening for t in recent):flags.append("Repeated opening")
    if any(SequenceMatcher(None,low,t.casefold()).ratio()>.8 for t in recent):flags.append("Similar to recent published content")
    if source and len(text)>30 and (low in source.casefold() or SequenceMatcher(None,low,source.casefold()).ratio()>.75):flags.append("May copy source wording")
    product=prefs.get("product").get("name","")
    if product and product.casefold() in low and product.casefold() not in source.casefold():flags.append("Review whether the product mention is useful")
    if re.search(r"\b(\d+%|\$\d+|our customers|my experience)\b",low):flags.append("Verify personal, customer, or numeric claims")
    banned_custom=(prefs.get("brand_voice").get("Banned phrases","")+"\n"+prefs.get("voice").get("hate","")).splitlines()
    if any(phrase.strip().casefold() in low for line in banned_custom for phrase in line.split(",") if phrase.strip()):
        flags.append("Contains a phrase you asked to avoid")
    closing=re.split(r"[.!?]",low.rstrip(".!?"))[-1].strip()
    if len(closing)>15 and any(t.casefold().rstrip(".!?").endswith(closing) for t in recent):
        flags.append("Repeated closing or call to action")
    emojis="".join(c for c in text if ord(c)>=0x1f300)
    if emojis and any("".join(c for c in t if ord(c)>=0x1f300)==emojis for t in recent):
        flags.append("Repeated emoji pattern")
    if product and product.casefold() in low and sum(product.casefold() in t.casefold() for t in recent[:10])>=3:
        flags.append("Frequent product mentions in recent posts")
    if text.count("!")>2:flags.append("Many exclamation marks; consider a calmer tone")
    return flags

def local_score(item):
    text=item["text"].casefold()
    interests=prefs.get("interests")
    matches=[t for t in interests if t.casefold() in text]
    watched=db.one("SELECT * FROM social_watch WHERE platform=? AND lower(handle)=? AND enabled=1",(item["platform"],item["username"].lower().lstrip("@")))
    if item["platform"]=="x" and not watched:
        watched=db.one("SELECT * FROM watched_accounts WHERE lower(username)=? AND enabled=1",(item["username"].lower(),))
    score=min(45,len(matches)*15)
    reasons=["Matches "+", ".join(matches[:3])] if matches else []
    if "?" in text:score+=10;reasons.append("Contains a question")
    if watched:score+={"High":25,"Normal":15,"Low":5}.get(watched["priority"],0);reasons.append("Watched account")
    product=prefs.get("product").get("name","")
    if product and product.casefold() in text:score+=20;reasons.append("Mentions your product")
    if item.get("content_kind") in {"mention","comment"}:score+=15;reasons.append("A mention or comment")
    timestamp=item.get("posted_at") or item["imported_at"]
    try:
        if datetime.fromisoformat(timestamp.replace("Z","+00:00"))>datetime.now(timezone.utc)-timedelta(days=1):score+=10
    except (ValueError,TypeError):pass
    metrics=json.loads(item.get("metrics") or "{}")
    engagement=sum(v for v in metrics.values() if isinstance(v,(int,float)) and v>=0)
    score+=min(10,int(engagement**.5))
    return min(100,score),"; ".join(reasons) or "Manually selected for review"

async def analyze(item_id,style="",draft_id=None):
    item=db.one("SELECT * FROM feed_items WHERE id=?",(item_id,))
    if not item or item["ignored"]:raise ValueError("This item is unavailable or ignored.")
    if db.one("SELECT 1 FROM social_mutes WHERE platform=? AND lower(author)=?",(item["platform"],item["username"].lower())):
        raise ValueError("This author is muted.")
    draft=await ws.generate_reply(item_id,style,draft_id)
    score,reason=local_score(item)
    db.execute("UPDATE feed_items SET analyzed=1,priority=?,reason=? WHERE id=?",(score,reason,item_id))
    if draft.get("skipped"):return draft
    kind="reply" if item["content_kind"]=="comment" or item["platform"] in {"x","threads"} else "comment"
    account=provider(item["platform"]).account.get("account_id","")
    db.execute("UPDATE drafts SET platform=?,account_id=?,kind=?,quality=?,score=? WHERE id=?",
        (item["platform"],account,kind,json.dumps(quality(draft["text"],item["text"])),score,draft["id"]))
    if score>=60 and prefs.get("notify_priority"):ws.notify("A high-priority social response is ready for review.")
    if item["content_kind"]=="mention" and prefs.get("notify_mentions"):ws.notify("An imported mention is ready for review.")
    return ws.get_draft(draft["id"])

async def sync(platform,kind="feed",target="",watch_id=None):
    p=provider(platform)
    items=await (p.get_mentions() if kind=="mentions" else p.get_comments(target) if kind=="comments" else p.get_feed(account_id=target or None))
    if not p.tokens().get("access_token"):return []
    imported=[]
    for value in items[:prefs.get("social_max_feed")]:
        if kind=="mentions":value["content_kind"]="mention"
        item=ingest(value,"API "+("Watchlist" if watch_id else kind))
        if item:imported.append(item)
    db.execute("UPDATE social_accounts SET last_sync=?,api_status='Connected' WHERE platform=?",(db.now(),platform))
    return imported

async def monitor():
    if not prefs.get("assistant_mode"):return
    for account in db.rows("SELECT * FROM social_accounts ORDER BY COALESCE(last_sync,'')"):
        platform=account["platform"]
        next_poll=db.get_setting("social_next_poll_"+platform,"")
        if next_poll>db.now():continue
        db.set_setting("social_next_poll_"+platform,(datetime.now(timezone.utc)+timedelta(minutes=prefs.get("poll_minutes"))).isoformat())
        try:
            caps=provider(platform).capabilities()
            if caps.get("can_read_feed"):await sync(platform)
            elif caps.get("can_read_comments"):await sync(platform,"comments")
        except Exception:
            if prefs.get("notify_connections"):ws.notify(CATALOG[platform]["name"]+" needs attention. Check Connected Accounts.")
        break
    watch=db.one("SELECT * FROM social_watch WHERE enabled=1 AND (next_check IS NULL OR next_check<=?) ORDER BY COALESCE(next_check,''),id LIMIT 1",(db.now(),))
    if watch:
        next_time=(datetime.now(timezone.utc)+timedelta(minutes=prefs.get("poll_minutes"))).isoformat()
        db.execute("UPDATE social_watch SET next_check=?,last_checked=? WHERE id=?",(next_time,db.now(),watch["id"]))
        try:
            p=provider(watch["platform"])
            if not p.capabilities().get("can_read_feed"):raise ValueError("Use Open Original; automatic access is unavailable for this account.")
            items=await sync(watch["platform"],target=watch["handle"],watch_id=watch["id"])
            new=[i for i in items if not i["analyzed"]]
            if watch["auto_draft"]:
                for item in new[:2]:await analyze(item["id"])
            db.execute("UPDATE social_watch SET error='',last_seen_id=? WHERE id=?",(items[0]["external_id"] if items else watch["last_seen_id"],watch["id"]))
            if new and watch["notifications"]:ws.notify(str(len(new))+" watchlist items are ready for review.")
        except Exception as error:
            db.execute("UPDATE social_watch SET error=? WHERE id=?",(str(error) if isinstance(error,ValueError) else "API access unavailable. Use Open Original or test the connection.",watch["id"]))
    # At most two unreviewed local items per pass; global AI cap still applies.
    for item in db.rows("""SELECT f.id FROM feed_items f WHERE ignored=0 AND analyzed=0
        AND NOT EXISTS(SELECT 1 FROM drafts d WHERE d.feed_id=f.id) ORDER BY imported_at DESC LIMIT 2"""):
        try:await analyze(item["id"])
        except Exception:break

def trends():
    recent=db.rows("SELECT * FROM feed_items WHERE ignored=0 AND imported_at>=? ORDER BY imported_at DESC LIMIT 1000",((datetime.now(timezone.utc)-timedelta(days=2)).isoformat(),))
    topics=list(dict.fromkeys(prefs.get("interests")+[r["name"] for r in db.rows("SELECT name FROM tracked_topics WHERE enabled=1")]))
    tags={}
    for item in recent:
        for tag in set(re.findall(r"#[\w]{3,30}",item["text"])):tags[tag]=tags.get(tag,0)+1
    topics+= [tag for tag,count in tags.items() if count>=2 and tag not in topics]
    boundary=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
    result=[]
    for topic in topics[:75]:
        matches=[x for x in recent if topic.casefold() in x["text"].casefold()]
        now=[x for x in matches if x["imported_at"]>=boundary];before=len(matches)-len(now)
        if not now:continue
        result.append({"name":topic,"platforms":sorted({x["platform"] for x in now}),"current":len(now),"previous":before,
            "velocity":len(now)-before,"related":[{"id":x["id"],"text":x["text"][:400],"url":x["url"],"platform":x["platform"]} for x in now[:5]],
            "reason":"Appears in your tracked interests or observed hashtags.","note":"Observed local imports in the last 24 hours versus the previous 24 hours. Not a platform-wide trend or virality prediction."})
    return sorted(result,key=lambda x:(x["velocity"],x["current"]),reverse=True)[:20]

def brief():
    drafts=db.one("SELECT COUNT(*) n FROM drafts WHERE status='draft'")["n"]
    return {"needs_review":drafts,"high_priority_count":db.one("SELECT COUNT(*) n FROM drafts WHERE status=\'draft\' AND score>=60")["n"],"high_priority":db.rows("SELECT * FROM feed_items WHERE ignored=0 AND priority>=60 ORDER BY priority DESC LIMIT 5"),
        "mentions":db.one("SELECT COUNT(*) n FROM feed_items WHERE ignored=0 AND content_kind='mention'")["n"],
        "comments":db.one("SELECT COUNT(*) n FROM feed_items WHERE ignored=0 AND content_kind='comment'")["n"],
        "scheduled":db.rows("SELECT s.*,d.text,d.platform FROM scheduled_posts s JOIN drafts d ON d.id=s.draft_id WHERE s.status='pending' ORDER BY due_at LIMIT 5"),
        "trends":trends()[:4],"recommendation":f"{drafts} drafts are waiting. Review the most relevant items; there is no posting-volume target."}
