import json
from datetime import datetime,timedelta,timezone
from urllib.parse import urlencode
from fastapi import APIRouter
from pydantic import BaseModel,Field
from .. import database as db,preferences as prefs,workspace as ws
from ..providers import provider as ai_provider
from . import workspace as social
from .catalog import CATALOG,definition
from .registry import provider

router=APIRouter(prefix="/api/social")

class Import(BaseModel):
    platform:str
    text:str=Field(min_length=1,max_length=30000)
    url:str=Field(default="",max_length=2048)
    author:str=Field(default="",max_length=150)
    kind:str="post"

@router.get("/feed")
def feed(platform:str="",filter:str="all"):
    sql="""SELECT f.* FROM feed_items f WHERE NOT EXISTS(SELECT 1 FROM social_mutes m
       WHERE m.platform=f.platform AND lower(m.author)=lower(f.username))"""
    args=[]
    if platform:definition(platform);sql+=" AND platform=?";args.append(platform)
    if filter=="ignored":sql+=" AND ignored=1"
    else:sql+=" AND ignored=0"
    if filter in {"mentions","comments"}:sql+=" AND content_kind=?";args.append(filter[:-1])
    if filter=="high":sql+=" AND priority>=60"
    if filter=="favorites":sql+=" AND (source LIKE '%Watchlist%' OR EXISTS(SELECT 1 FROM social_watch w WHERE w.platform=f.platform AND lower(w.handle)=lower(f.username) AND w.category='favorite'))"
    if filter=="questions":sql+=" AND text LIKE '%?%'"
    return db.rows(sql+" ORDER BY priority DESC,imported_at DESC LIMIT ?",[*args,prefs.get("social_max_feed")])

@router.post("/import")
def import_content(data:Import):
    if data.kind not in {"post","mention","comment"}:raise ValueError("Choose a post, mention, or comment.")
    return social.manual_import(data.platform,data.text,data.url,data.author,data.kind)

@router.post("/analyze")
async def analyze(data:dict):
    return await social.analyze(str(data.get("id","")),str(data.get("style","")),data.get("draft_id"))

@router.post("/sync/{platform}")
async def sync(platform:str,data:dict):
    if data.get("kind","feed") not in {"feed","mentions","comments"}:raise ValueError("Choose feed, mentions, or comments.")
    return {"items":await social.sync(platform,data.get("kind","feed"),str(data.get("target","")))}

@router.get("/inbox")
def inbox(tab:str="review",platform:str=""):
    rows=db.rows("""SELECT d.*,f.username,f.text source_text,f.content_kind,f.url source_url,f.source,
        f.reason opportunity_reason FROM drafts d LEFT JOIN feed_items f ON f.id=d.feed_id WHERE d.status<>'deleted' ORDER BY d.score DESC,d.id DESC LIMIT 500""")
    if platform:rows=[d for d in rows if d["platform"]==platform]
    states={"review":{"draft","failed"},"approved":{"approved"},"scheduled":{"scheduled"},"ignored":{"skipped"}}
    if tab in states:return [d for d in rows if d["status"] in states[tab]]
    rows=[d for d in rows if d["status"] not in {"published","skipped"}]
    if tab=="high":return [d for d in rows if d["score"]>=60]
    if tab in {"mentions","comments"}:return [d for d in rows if d["content_kind"]==tab[:-1]]
    if tab=="questions":return [d for d in rows if "?" in (d["source_text"] or "")]
    if tab=="favorites":return [d for d in rows if "Watchlist" in (d["source"] or "") or "Watched account" in (d["opportunity_reason"] or "")]
    if tab=="product":return [d for d in rows if "product" in (d["opportunity_reason"] or "").lower()]
    if tab=="trending":
        topics=[t["name"].lower() for t in social.trends()]
        return [d for d in rows if any(t in (d["source_text"] or "").lower() for t in topics)]
    return rows

class Draft(BaseModel):
    platform:str="x"
    text:str=Field(max_length=20000)
    kind:str="original"
    feed_id:str|None=None
    media_ids:list[str]=Field(default_factory=list,max_length=4)
    generated_text:str=Field(default="",max_length=20000)

@router.post("/drafts")
def create_draft(data:Draft):
    definition(data.platform)
    if data.feed_id:
        source=db.one("SELECT * FROM feed_items WHERE id=?",(data.feed_id,))
        if not source or source["platform"]!=data.platform:raise ValueError("The source and target platform must match.")
    draft=ws.save_draft(data.kind,data.text,data.feed_id,generated=data.generated_text,platform=data.platform,media_ids=data.media_ids)
    db.execute("UPDATE drafts SET quality=? WHERE id=?",(json.dumps(social.quality(data.text,draft.get("source_text") or "")),draft["id"]))
    return ws.get_draft(draft["id"])

@router.put("/drafts/{id}")
def edit_draft(id:int,data:Draft):
    current=ws.get_draft(id)
    if current["platform"]!=data.platform:raise ValueError("Create a separate version for another platform.")
    draft=ws.save_draft(data.kind,data.text,data.feed_id,draft_id=id,platform=data.platform,media_ids=data.media_ids,generated=data.generated_text)
    db.execute("UPDATE drafts SET quality=? WHERE id=?",(json.dumps(social.quality(data.text,draft.get("source_text") or "")),id))
    return ws.get_draft(id)

@router.post("/drafts/{id}/manual")
def manual(id:int):
    d=ws.require_approved(id)
    source=db.one("SELECT * FROM feed_items WHERE id=?",(d["feed_id"],)) if d["feed_id"] else None
    url=source["url"] if source and source["url"] else CATALOG[d["platform"]]["home"]
    if d["platform"]=="x":
        params={"text":d["text"]}
        if source and source["id"].isdigit():params["in_reply_to"]=source["id"]
        url="https://x.com/intent/tweet?"+urlencode(params)
    ws.activity("manual_composer_opened",d,status="opened",channel="manual")
    return {"url":url,"text":d["text"],"media_ids":json.loads(d["media_ids"]),"note":"Draft copied/opened for manual publishing. No publication is recorded."}

@router.post("/drafts/{id}/schedule")
def schedule(id:int,data:dict):
    d=ws.require_approved(id)
    mode=data.get("delivery","manual")
    if mode not in {"api","manual"}:raise ValueError("Choose API publishing or a manual reminder.")
    if mode=="api":
        if not provider(d["platform"]).capabilities()["can_publish"]:raise ValueError("Use a manual publishing reminder for this platform.")
        if json.loads(d["media_ids"]) and (not provider(d["platform"]).capabilities()["can_upload_images"] or any((db.one("SELECT mime FROM media WHERE id=?",(id,)) or {}).get("mime") not in {"image/jpeg","image/png"} for id in json.loads(d["media_ids"]))):raise ValueError("Attached media requires a manual reminder.")
    result=ws.schedule(id,str(data.get("due_at","")),str(data.get("timezone","")),manual=mode=="manual")
    db.execute("UPDATE scheduled_posts SET delivery=? WHERE draft_id=?",(mode,id))
    return result

@router.post("/drafts/{id}/duplicate")
def duplicate(id:int,data:dict):
    d=ws.get_draft(id);platform=str(data.get("platform",""));definition(platform)
    return ws.save_draft("original",d["text"],platform=platform,media_ids=json.loads(d["media_ids"]))

@router.post("/mute")
def mute(data:dict):
    platform=str(data.get("platform",""));definition(platform)
    db.execute("INSERT OR IGNORE INTO social_mutes VALUES(?,?)",(platform,str(data.get("author","")).lower()))
    return {"muted":True}

@router.get("/trends")
def trends():return social.trends()

@router.get("/brief")
def brief():return social.brief()

@router.get("/analytics")
def analytics():
    return {"activity":db.rows("SELECT platform,action,status,COUNT(*) count FROM activity GROUP BY platform,action,status"),
       "topics":db.rows("SELECT topic,COUNT(*) count FROM activity WHERE status='published' AND topic<>'' GROUP BY topic ORDER BY count DESC LIMIT 10"),
       "accounts":db.rows("SELECT platform,target_account,COUNT(*) count FROM activity WHERE status='published' AND target_account<>'' GROUP BY platform,target_account ORDER BY count DESC LIMIT 10"),
       "drafts":db.rows("SELECT platform,status,COUNT(*) count FROM drafts GROUP BY platform,status"),
       "acceptance":db.rows("""SELECT platform,COUNT(*) generated,
           SUM(CASE WHEN EXISTS(SELECT 1 FROM activity a WHERE a.draft_id=d.id AND a.action='approved') THEN 1 ELSE 0 END) accepted
           FROM drafts d WHERE generated_text<>'' GROUP BY platform"""),
       "note":"Counts represent locally recorded actions. Manual opens are not published posts; no impressions or follower growth are estimated."}

@router.post("/suggest")
async def suggest(data:dict):
    task=str(data.get("task","Write"))[:120];platform=str(data.get("platform","x"));definition(platform)
    text=str(data.get("text",""))[:12000]
    context={"my_profile":prefs.get("my_profile"),"brand_voice":prefs.get("brand_voice"),"product":prefs.get("product")}
    if task=="Weekly plan":
        from ..planner import weekly_plan
        return await weekly_plan(platform,str(data.get("timezone","UTC")),text)
    result=await ws.ai_call(lambda:ai_provider().rewrite(text,task+" for "+CATALOG[platform]["name"]+
        ". Create original, useful content; never copy a creator's wording or invent metrics. Suggestions only. Respect the target's "+str(CATALOG[platform]["limit"])+" character limit. Truthful context: "+json.dumps(context)))
    return {"text":result,"quality":social.quality(result,text)}

@router.get("/planner")
def saved_plan():
    return db.get_setting("last_weekly_plan",{})

@router.get("/ideas")
def ideas():return db.rows("SELECT * FROM ideas ORDER BY id DESC")

@router.post("/ideas")
def add_idea(data:dict):
    title=str(data.get("title","")).strip()[:200];text=str(data.get("text","")).strip()[:20000]
    if not title or not text:raise ValueError("Add a title and idea text.")
    url=str(data.get("url",""))[:2048]
    if url and not url.startswith("https://"):raise ValueError("Use an HTTPS reference link.")
    return {"id":db.execute("INSERT INTO ideas(title,text,url,kind,created_at) VALUES(?,?,?,?,?)",(title,text,url,str(data.get("kind","thought"))[:40],db.now()))}

@router.delete("/ideas/{id}")
def delete_idea(id:int):db.execute("DELETE FROM ideas WHERE id=?",(id,));return {"deleted":True}

@router.get("/watch")
def watch(category:str="favorite"):return db.rows("SELECT * FROM social_watch WHERE category=? ORDER BY id DESC",(category,))

@router.post("/watch")
def save_watch(data:dict):
    platform=str(data.get("platform",""));definition(platform)
    handle=str(data.get("handle","")).strip().lstrip("@")[:150]
    if not handle:raise ValueError("Add an account ID, handle, brand or keyword.")
    category=str(data.get("category","favorite"))
    if category not in {"favorite","competitor","industry","keyword","brand"}:raise ValueError("Choose a watch category.")
    priority=data.get("priority","Normal")
    if priority not in {"Low","Normal","High"}:raise ValueError("Choose a priority.")
    url=social.safe_url(platform,str(data.get("url","")))
    if data.get("id"):
        existing=db.one("SELECT id FROM social_watch WHERE id=?",(int(data["id"]),))
        if not existing:raise ValueError("Watch entry not found.")
        db.execute("DELETE FROM social_watch WHERE id=?",(int(data["id"]),))
    id=db.execute("""INSERT INTO social_watch(platform,handle,url,category,priority,topics,enabled,notifications,auto_draft)
      VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(platform,handle,category) DO UPDATE SET url=excluded.url,priority=excluded.priority,
      topics=excluded.topics,enabled=excluded.enabled,notifications=excluded.notifications,auto_draft=excluded.auto_draft""",
      (platform,handle,url,category,priority,str(data.get("topics",""))[:1000],bool(data.get("enabled",True)),bool(data.get("notifications")),bool(data.get("auto_draft"))))
    return {"saved":True,"id":id}

@router.delete("/watch/{id}")
def delete_watch(id:int):db.execute("DELETE FROM social_watch WHERE id=?",(id,));return {"deleted":True}

@router.get("/market")
def market():
    watches=db.rows("SELECT * FROM social_watch WHERE category<>'favorite'")
    content=db.rows("SELECT platform,username,text,url FROM feed_items WHERE ignored=0 ORDER BY imported_at DESC LIMIT 500")
    return [{"watch":w,"matches":[x for x in content if w["handle"].casefold() in (x["username"]+" "+x["text"]).casefold() and x["platform"]==w["platform"]][:20]} for w in watches]

@router.delete("/accounts/{platform}/data")
async def delete_account_data(platform:str):
    definition(platform)
    async with ws.WRITE_LOCK:
        provider(platform).disconnect()
        with db.conn() as c:
            ids=[r[0] for r in c.execute("SELECT id FROM drafts WHERE platform=?",(platform,))]
            for id in ids:
                c.execute("DELETE FROM approved_content WHERE draft_id=?",(id,))
                c.execute("DELETE FROM scheduled_posts WHERE draft_id=?",(id,))
                c.execute("DELETE FROM media_usage WHERE draft_id=?",(id,))
            for table in ("drafts","feed_items","activity","actions","social_watch","social_mutes","social_usage"):
                c.execute("DELETE FROM "+table+" WHERE platform=?",(platform,))
    return {"deleted":True,"note":"Local account data deleted. This also removes that provider's local write-safety records."}
