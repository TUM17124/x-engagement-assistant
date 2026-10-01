"""Explicit local deletion. Remote social content is never deleted."""
from fastapi import APIRouter
from .. import database as db,workspace as ws,media
from .registry import provider
from .catalog import CATALOG
router=APIRouter(prefix="/api/social")

@router.delete("/data")
async def clear_data(data:dict):
    if data.get("confirm")!="DELETE":raise ValueError("Confirm local deletion by typing DELETE.")
    async with ws.WRITE_LOCK:
        for platform in CATALOG:
            provider(platform).disconnect()
        for row in db.rows("SELECT id FROM media"):
            try:media.media_path(row["id"]).unlink()
            except ValueError:pass
        with db.conn() as c:
            c.execute("PRAGMA secure_delete=ON")
            for table in ("approved_content","scheduled_posts","media_usage","drafts","feed_items","activity","actions",
                          "social_watch","social_mutes","social_usage","social_accounts","media","ideas","watched_accounts",
                          "tracked_topics","muted_accounts","muted_topics","notifications","ai_usage","search_usage","settings","app_meta"):
                c.execute("DELETE FROM "+table)
        with db.conn() as c:c.execute("VACUUM")
    return {"deleted":True,"note":"Local workspace cleared. AI and OAuth app credentials remain in OS storage until you delete them in Settings."}
