import asyncio
from datetime import datetime,timedelta,timezone
from . import database as db, preferences as prefs
from .workspace import publish, content_hash, get_draft, notify
from .discovery import poll_account,poll_topic

def recover():
    # Never replay an interrupted or missed write after a crash/restart.
    db.execute("UPDATE drafts SET status='uncertain' WHERE status='sending'")
    db.execute("UPDATE scheduled_posts SET status='uncertain',error='App stopped during publishing. Check X before rescheduling.' WHERE status='sending'")
    db.execute("UPDATE scheduled_posts SET status='missed',error='The app was not running at the scheduled time. Review and reschedule.' WHERE status='pending' AND due_at<?",(db.now(),))
    db.set_setting("scheduler_state","Running")

async def tick():
    current=db.now()
    for item in db.rows("SELECT * FROM scheduled_posts WHERE status='pending' ORDER BY due_at"):
        if item["due_at"] <= current:
            # Claim once, before network I/O. Failures require explicit review.
            with db.conn() as c:
                if not c.execute("UPDATE scheduled_posts SET status='sending' WHERE id=? AND status='pending'",(item["id"],)).rowcount:
                    continue
            try:
                draft=get_draft(item["draft_id"])
                if item["content_hash"] != content_hash(draft):
                    raise ValueError("Content changed after scheduling. Approve and schedule again.")
                await publish(item["draft_id"],scheduled=True)
                notify("Your approved scheduled post was published.")
            except Exception as error:
                message=str(error) if isinstance(error,ValueError) else "Scheduled publishing failed. Review the draft and X before retrying."
                db.execute("UPDATE scheduled_posts SET status='failed',error=? WHERE id=?",(message,item["id"]))
                notify("A scheduled post needs your review.")
        elif not item["notified"] and item["due_at"] <= (datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat():
            notify("Your approved scheduled post publishes in 10 minutes.")
            db.execute("UPDATE scheduled_posts SET notified=1 WHERE id=?",(item["id"],))
    db.set_setting("scheduler_heartbeat",current)

async def monitor():
    if not prefs.get("monitoring") or not prefs.get("read_access"):
        return
    # One account/topic per pass; each has a minimum 15-minute persisted interval.
    for table, function in (("watched_accounts",poll_account),("tracked_topics",poll_topic)):
        item=db.one(f"SELECT * FROM {table} WHERE enabled=1 AND (next_poll_at IS NULL OR next_poll_at<=?) ORDER BY CASE priority WHEN 'High' THEN 0 WHEN 'Normal' THEN 1 ELSE 2 END,id LIMIT 1",(db.now(),))
        if item:
            try:
                await function(item["id"])
            except Exception:
                # Poll functions persist safe user-facing errors; no provider bodies/keys are logged.
                pass

async def scheduler_loop():
    while True:
        try:
            await tick()
            db.set_setting("scheduler_state","Running")
        except Exception:
            db.set_setting("scheduler_state","Problem ? review Schedule")
        await asyncio.sleep(10)

async def monitor_loop():
    while True:
        await monitor()
        await asyncio.sleep(60)

async def run_workers():
    recover()
    tasks=[asyncio.create_task(scheduler_loop()),asyncio.create_task(monitor_loop())]
    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
        db.set_setting("scheduler_state","Stopped")
