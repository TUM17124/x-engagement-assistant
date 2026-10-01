"""Official API reads only. Monitoring is opt-in, bounded and persisted."""
from datetime import datetime,timedelta,timezone
from urllib.parse import urlencode
import re
from . import database as db, preferences as prefs, x_api
from .errors import ServiceError
from .workspace import import_post, generate_reply, notify

READ_ACCESS_MESSAGE = "This feature requires X API read access on your current developer plan."

def query_for(topic):
    words = [x.strip() for x in topic["keywords"].split(",") if x.strip()]
    if not words:
        raise ValueError("Add at least one keyword.")
    clean = lambda word: re.sub(r'[^\w\s-]', '',word).strip()
    terms = ['"'+clean(word)+'"' for word in words if clean(word)]
    query = "("+" OR ".join(terms)+")"
    for word in topic.get("excluded","").split(","):
        if clean(word):
            query += ' -"'+clean(word)+'"'
    languages = [x.strip() for x in topic.get("languages","en").split(",") if re.fullmatch("[a-z]{2}",x.strip())]
    if languages:
        query += " ("+" OR ".join("lang:"+x for x in languages)+")"
    return query + " -is:retweet"

def web_search(query):
    return "https://x.com/search?"+urlencode({"q":query,"src":"typed_query","f":"live"})

def check_access():
    if not prefs.get("read_access"):
        raise ValueError(READ_ACCESS_MESSAGE + " Use Open on X and paste a post instead.")
    paused = db.get_setting("discovery_blocked")
    if paused:
        raise ValueError(paused+" Use Test X connection, then Resume discovery in Settings.")
    until = db.get_setting("read_backoff_until")
    if until and until > db.now():
        raise ValueError("X API limit reached. Automatic discovery is paused until "+until)

async def read(path, params=None):
    check_access()
    try:
        return await x_api.read_endpoint(path, params)
    except ServiceError as error:
        if error.status == 429:
            db.set_setting("read_backoff_until",(datetime.now(timezone.utc)+timedelta(seconds=error.retry_after)).isoformat())
        elif error.status in {401,402,403}:
            db.set_setting("discovery_blocked",str(error))
        notify("X API access or limit reached. Automatic discovery paused.")
        raise

def ingest(payload, source, topic=""):
    users = {u["id"]:u for u in payload.get("includes",{}).get("users",[])}
    records = payload.get("data",[])
    if isinstance(records,dict):
        records=[records]
    imported=[]
    for post in records:
        author=users.get(post.get("author_id"),{})
        username=author.get("username")
        if not username:
            continue
        if db.one("SELECT 1 FROM feed_items WHERE id=?",(post["id"],)):
            continue
        if db.one("SELECT 1 FROM muted_accounts WHERE username=?",(username.lower(),)):
            continue
        imported.append(import_post(f"https://x.com/{username}/status/{post['id']}",post["text"],source=source,
            display_name=author.get("name",""),avatar=author.get("profile_image_url",""),
            posted_at=post.get("created_at"),metrics=post.get("public_metrics",{}),topic=topic))
    return imported

FIELDS={"tweet.fields":"created_at,public_metrics,author_id","expansions":"author_id",
        "user.fields":"username,name,profile_image_url"}

async def fetch_post(tweet_id):
    return ingest(await read("/tweets/"+tweet_id,FIELDS),"API import")

async def poll_account(account_id):
    account=db.one("SELECT * FROM watched_accounts WHERE id=?",(account_id,))
    if not account or not account["enabled"]:
        return []
    if account["next_poll_at"] and account["next_poll_at"]>db.now():
        raise ValueError("This account was checked recently. Open latest posts on X or wait for the next interval.")
    # Reserve interval before any request so errors/clicks cannot hammer an endpoint.
    next_time=(datetime.now(timezone.utc)+timedelta(minutes=prefs.get("poll_minutes"))).isoformat()
    db.execute("UPDATE watched_accounts SET next_poll_at=? WHERE id=?",(next_time,account_id))
    try:
        user=await read("/users/by/username/"+account["username"])
        params={**FIELDS,"max_results":10}
        if account["last_seen_id"]:
            params["since_id"]=account["last_seen_id"]
        payload=await read("/users/"+user["data"]["id"]+"/tweets",params)
        imported=ingest(payload,"Watchlist",account["topics"])
        ids=[p["id"] for p in payload.get("data",[])]
        if ids:
            db.execute("UPDATE watched_accounts SET last_seen_id=?,error='' WHERE id=?",(max(ids,key=int),account_id))
        if imported and account["notifications"]:
            notify("@"+account["username"]+" posted something new.")
        if account["ai_drafting"]:
            for item in imported[:3]:
                await generate_reply(item["id"])
        return imported
    except (ServiceError,ValueError) as error:
        db.execute("UPDATE watched_accounts SET error=? WHERE id=?",(str(error),account_id))
        raise

async def poll_topic(topic_id):
    topic=db.one("SELECT * FROM tracked_topics WHERE id=?",(topic_id,))
    if not topic or not topic["enabled"]:
        return []
    if topic["next_poll_at"] and topic["next_poll_at"]>db.now():
        raise ValueError("This topic was checked recently. Use X web search or wait for the next interval.")
    db.execute("UPDATE tracked_topics SET next_poll_at=? WHERE id=?",
               ((datetime.now(timezone.utc)+timedelta(minutes=prefs.get("poll_minutes"))).isoformat(),topic_id))
    try:
        from .search import recent_search
        result=await recent_search(topic["query"] or query_for(topic),10,topic["name"])
        db.execute("UPDATE tracked_topics SET error=? WHERE id=?",("" if result["mode"]=="api" else result["message"],topic_id))
        return result["items"]
    except (ServiceError,ValueError) as error:
        db.execute("UPDATE tracked_topics SET error=? WHERE id=?",(str(error),topic_id))
        raise
