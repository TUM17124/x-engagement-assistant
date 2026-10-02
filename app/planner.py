"""Local weekly planning. Suggestions never become schedules or approvals."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from . import database as db, preferences as prefs, workspace as ws
from .providers import provider
from .social.catalog import CATALOG, definition
from .social.workspace import trends

async def weekly_plan(platform="x", timezone_name="UTC", goal=""):
    definition(platform)
    try:
        zone = ZoneInfo(timezone_name)
    except (ValueError, KeyError):
        raise ValueError("Choose a valid timezone for your weekly plan.") from None
    start = datetime.now(zone).date()
    context = {"platform": CATALOG[platform]["name"], "timezone": timezone_name,
        "dates": [(start + timedelta(days=i)).isoformat() for i in range(7)],
        "goal": goal[:2000], "interests": prefs.get("interests"),
        "topics": db.rows("SELECT name,keywords FROM tracked_topics WHERE enabled=1 LIMIT 20"),
        "my_profile": prefs.get("my_profile"), "brand_voice": prefs.get("brand_voice"),
        "product": prefs.get("product"), "trends": trends()[:5],
        "ideas": db.rows("SELECT title,text FROM ideas ORDER BY id DESC LIMIT 8"),
        "recent_published": db.rows("SELECT platform,final_text FROM activity WHERE status='published' ORDER BY id DESC LIMIT 12")}
    selected = provider()
    text = (await ws.ai_call(lambda: selected.generate_plan(context))).strip()
    if not text or text.upper().strip(' .!') == "SKIP":
        raise ValueError("The AI did not return a weekly plan. Add interests or a goal and try again. Your previous plan is unchanged.")
    result = {"text":text, "quality":[], "platform":platform, "timezone":timezone_name,
        "generated_at":db.now(), "provider":prefs.get("ai_provider"), "model":selected.model,
        "dates":context["dates"]}
    db.set_setting("last_weekly_plan", result)
    return result
