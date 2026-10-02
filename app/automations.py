"""Persistent local, bounded read/draft workflows. No publishing tools are permitted."""
import asyncio
import json
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from . import database as db,workspace as ws,preferences as prefs
from .command_tools import Automation,REGISTRY
from .command_bus import event
from .chatgpt_auth import ChatGPTError

LOCK=asyncio.Lock()

def next_due(config,after=None):
    now=after or datetime.now(timezone.utc)
    if config.trigger=="watch":return (now+timedelta(minutes=config.interval_minutes)).isoformat()
    zone=ZoneInfo(config.timezone)
    hour,minute=map(int,config.time.split(":"))
    if hour>23 or minute>59:raise ValueError("Choose a valid daily time.")
    local=now.astimezone(zone)
    due=local.replace(hour=hour,minute=minute,second=0,microsecond=0)
    if due<=local:due+=timedelta(days=1)
    # Normalize a skipped wall time forward through UTC; do not run twice on a repeated hour.
    return due.astimezone(timezone.utc).isoformat()

def create(config):
    ZoneInfo(config.timezone)
    if config.trigger=="watch" and not config.username:raise ValueError("Choose an account to watch.")
    encoded=json.dumps(config.model_dump(),sort_keys=True)
    existing=db.one("SELECT * FROM automations WHERE config=? AND status<>'deleted'",(encoded,))
    if existing:return existing
    id=db.execute("INSERT INTO automations(name,trigger,config,timezone,status,next_run,created_at) VALUES(?,?,?,?,?,?,?)",
        (config.name,config.trigger,encoded,config.timezone,"active",next_due(config),db.now()))
    event(None,"automation_created",automation_id=id)
    return db.one("SELECT * FROM automations WHERE id=?",(id,))

def set_state(id,state):
    item=db.one("SELECT * FROM automations WHERE id=?",(id,))
    if not item or item["status"]=="deleted":raise ValueError("Automation not found.")
    if item["status"]=="running":
        if state=="active":raise ValueError("Automation is currently running.")
        # Cooperative cancellation between network operations; no publishing occurs.
    config=Automation.model_validate_json(item["config"])
    db.execute("UPDATE automations SET status=?,next_run=?,error='' WHERE id=?",(state,next_due(config),id))
    event(None,"automation_"+state,automation_id=id)
    return db.one("SELECT * FROM automations WHERE id=?",(id,))

def recover():
    db.execute("UPDATE automations SET status='paused',error='Interrupted by shutdown. Review run history and resume; partial work is retained.' WHERE status='running'")
    db.execute("UPDATE automation_runs SET status='interrupted',finished_at=? WHERE status='running'",(db.now(),))
    db.execute("UPDATE action_requests SET status='uncertain',error='App stopped during execution. Inspect current state before retrying.' WHERE status='executing'")
    db.execute("UPDATE terminal_commands SET status='interrupted',finished_at=? WHERE status='running'",(db.now(),))

async def step(run_id,key,tool_name,arguments,automation_id):
    from .command_tools import invoke
    spec=REGISTRY[tool_name]
    if not spec.automation_allowed:raise ValueError("This tool cannot run in an automation.")
    old=db.one("SELECT * FROM automation_steps WHERE run_id=? AND step_key=?",(run_id,key))
    if old:
        if old["status"]=="completed":return json.loads(old["result"])
        raise ValueError("A prior step was interrupted. Review the run rather than automatically replaying it.")
    db.execute("INSERT INTO automation_steps(run_id,step_key,status) VALUES(?,?,'running')",(run_id,key))
    event(None,"tool_requested",tool_name,automation_id=automation_id)
    value=await invoke(spec,spec.schema.model_validate(arguments))
    from .command_bus import redact
    value=redact(value)
    db.execute("UPDATE automation_steps SET status='completed',result=? WHERE run_id=? AND step_key=?",(json.dumps(value),run_id,key))
    event(None,"tool_succeeded",tool_name,automation_id=automation_id)
    return value

async def tick():
    if db.get_setting("automations_paused",False):return
    async with LOCK:
        current=datetime.now(timezone.utc)
        for item in db.rows("SELECT * FROM automations WHERE status='active' AND next_run<=? ORDER BY next_run LIMIT 1",(current.isoformat(),)):
            config=Automation.model_validate_json(item["config"])
            if current-datetime.fromisoformat(item["next_run"])>timedelta(minutes=15):
                db.execute("INSERT OR IGNORE INTO automation_runs(automation_id,started_at,finished_at,status,summary) VALUES(?,?,?,'missed','App was closed or busy. No catch-up burst was run.')",(item["id"],item["next_run"],db.now()))
                db.execute("UPDATE automations SET next_run=? WHERE id=?",(next_due(config),item["id"]));continue
            with db.conn() as c:
                if not c.execute("UPDATE automations SET status='running' WHERE id=? AND status='active'",(item["id"],)).rowcount:continue
                run=c.execute("INSERT INTO automation_runs(automation_id,started_at,status) VALUES(?,?,'running')",(item["id"],item["next_run"])).lastrowid
            event(None,"automation_start",automation_id=item["id"])
            drafts=[]
            eligible_ids=None
            try:
                if config.platform=="x" and config.query:
                    found=await step(run,"search","social.search",{"query":config.query,"author":config.username},item["id"])
                    eligible_ids=set(found.get("ids",[]))
                    if found.get("mode")=="web":raise ValueError("Official paid X search unavailable. Use Open Search on X and import posts; automation paused.")
                else:
                    result=await step(run,"scan","social.scanFeed",{"platform":config.platform,"target":config.username},item["id"])
                    if not any(s.get("ids") for s in result.get("scans",[])):
                        # Existing imported sources remain useful, but a read failure should be visible.
                        if any("unavailable" in s.get("message","").lower() for s in result.get("scans",[])):
                            raise ValueError("Official social read access unavailable. Reconnect or use manual import.")
                rows=db.rows("""SELECT f.* FROM feed_items f WHERE platform=? AND ignored=0
                  AND NOT EXISTS(SELECT 1 FROM drafts d WHERE d.feed_id=f.id)
                  ORDER BY priority DESC,imported_at DESC LIMIT 50""",(config.platform,))
                terms=[t.strip().lower() for t in config.topics.split(",") if t.strip()]
                for row in rows:
                    if eligible_ids is not None and row["id"] not in eligible_ids:continue
                    if len(drafts)>=config.max_drafts:break
                    state=db.one("SELECT status FROM automations WHERE id=?",(item["id"],))
                    if not state or state["status"]!="running" or db.get_setting("automations_paused",False):
                        raise asyncio.CancelledError()
                    if config.username and row["username"].lower().lstrip("@")!=config.username.lower().lstrip("@"):continue
                    if terms and not any(t in row["text"].lower() for t in terms):continue
                    d=await step(run,"draft:"+row["id"],"content.draftReply",{"post_id":row["id"]},item["id"])
                    if d.get("id"):drafts.append(d["id"])
                summary=json.dumps({"draft_ids":drafts,"message":f"{len(drafts)} draft(s) prepared. Waiting for human review; nothing was sent."})
                state="waiting-for-approval" if drafts else "active"
                db.execute("UPDATE automations SET status=?,next_run=?,error='' WHERE id=? AND status='running'",(state,next_due(config),item["id"]))
                db.execute("UPDATE automation_runs SET status='completed',finished_at=?,summary=? WHERE id=?",(db.now(),summary,run))
                event(None,"automation_completion",automation_id=item["id"])
                if drafts:ws.notify(str(len(drafts))+" automation drafts are ready for approval.")
            except BaseException as error:
                if isinstance(error,asyncio.CancelledError):state,message="paused","Automation interrupted; completed drafts are retained."
                elif isinstance(error,ChatGPTError):state,message=("needs-auth" if error.state in {"Disconnected","Authorization expired","Plan usage disabled"} else "paused"),str(error)
                else:state,message="failed",str(error) if isinstance(error,ValueError) else "Connection or AI operation failed. Check Settings and resume explicitly."
                db.execute("UPDATE automations SET status=?,error=?,next_run=? WHERE id=? AND status='running'",(state,message,next_due(config),item["id"]))
                db.execute("UPDATE automation_runs SET status=?,finished_at=?,summary=? WHERE id=?",(state,db.now(),json.dumps({"draft_ids":drafts,"message":message}),run))
                event(None,"automation_failed",status=state,automation_id=item["id"])
                ws.notify("An automation needs attention. Review Automations.")
                if isinstance(error,asyncio.CancelledError):raise

async def loop():
    recover()
    while True:
        try:await tick()
        except asyncio.CancelledError:raise
        except Exception:pass
        await asyncio.sleep(30)
