"""Cost-aware official recent search plus same-query web fallback."""
from datetime import datetime,timedelta,timezone
import asyncio
import re
from . import database as db, preferences as prefs, x_api
from .errors import ServiceError
from .discovery import FIELDS, ingest, web_search

SEARCH_LOCK=asyncio.Lock()
def build_query(query, language="", exclude_retweets=True, exclude_replies=False, author=""):
    query=query.strip()
    if not query:
        raise ValueError("Enter search keywords or a boolean query.")
    if language:
        if not re.fullmatch("[a-z]{2}",language):
            raise ValueError("Use a two-letter language code.")
        query+=" lang:"+language
    if exclude_retweets and "-is:retweet" not in query:
        query+=" -is:retweet"
    if exclude_replies and "-is:reply" not in query:
        query+=" -is:reply"
    if author:
        author=author.lstrip("@")
        if not re.fullmatch("[A-Za-z0-9_]{1,15}",author):
            raise ValueError("Use a valid author username.")
        query+=" from:"+author
    if len(query)>512:
        raise ValueError("Keep the query within 512 characters for recent search.")
    return query

def status():
    day=db.now()[:10]
    usage=db.one("SELECT COUNT(*) searches,COALESCE(SUM(retrieved),0) posts FROM search_usage WHERE substr(created_at,1,10)=?",(day,))
    return {"state":db.get_setting("search_access","Not tested"),"searches_today":usage["searches"],
            "posts_retrieved_today":usage["posts"],"daily_limit":prefs.get("daily_search_limit"),
            "blocked":db.get_setting("search_blocked",""),"mode":prefs.get("discovery_mode")}

async def recent_search(query,max_results=20,topic=""):
    if not 10<=max_results<=100:
        raise ValueError("Choose 10-100 maximum results.")
    fallback={"query":query,"web_url":web_search(query),"items":[],"mode":"web"}
    if prefs.get("discovery_mode")=="web":
        return {**fallback,"message":"X Web Search selected. Open Search on X, then import a post."}
    async with SEARCH_LOCK:
        if db.get_setting("search_blocked"):
            return {**fallback,"message":"Paid X API search is unavailable on your current plan.","state":status()["state"]}
        until=db.get_setting("read_backoff_until")
        if until and until>db.now():
            return {**fallback,"message":"X API rate limit reached. Search is paused until "+until}
        if status()["searches_today"]>=prefs.get("daily_search_limit"):
            return {**fallback,"message":"Daily API search limit reached. You can still use X web search."}
        attempt=db.execute("INSERT INTO search_usage(created_at,retrieved,status) VALUES(?,0,'pending')",(db.now(),))
        try:
            payload=await x_api.read_endpoint("/tweets/search/recent",{**FIELDS,"query":query,"max_results":max_results})
        except ServiceError as error:
            db.execute("UPDATE search_usage SET status=? WHERE id=?",(str(error.status),attempt))
            if error.status in {402,403,404}:
                db.set_setting("search_blocked",str(error.status))
                db.set_setting("search_access","Requires Credits" if error.status==402 else "Requires Access")
                return {**fallback,"message":"Paid X API search is unavailable on your current plan.","technical":f"X HTTP {error.status}"}
            if error.status==429:
                db.set_setting("read_backoff_until",(datetime.now(timezone.utc)+timedelta(seconds=error.retry_after)).isoformat())
            return {**fallback,"message":str(error),"technical":f"X HTTP {error.status}"}
        except RuntimeError:
            db.execute("UPDATE search_usage SET status='authentication_required' WHERE id=?",(attempt,))
            return {**fallback,"message":"Connect X or add a read bearer token in Settings. You can use X web search meanwhile."}
        records=payload.get("data",[])
        db.execute("UPDATE search_usage SET retrieved=?,status='success' WHERE id=?",(len(records),attempt))
        db.set_setting("search_access","Available")
        items=ingest(payload,"API search",topic)
        ids=[p["id"] for p in records]
        return {"mode":"api","items":items,"ids":ids,"retrieved":len(records),"query":query,
                "web_url":web_search(query),"message":f"X API Search: Available - {len(records)} posts retrieved."}
