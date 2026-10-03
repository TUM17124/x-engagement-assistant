import os
import sys
from urllib.parse import urlsplit
from . import database as db
from .secrets import store, PUBLIC_SECRET_NAMES

DEFAULTS = {
    "check_updates": True, "claude_workspace_id": "",
    "assistant_mode": False, "social_daily_request_cap": 100, "social_max_feed": 200,
    "my_profile": {}, "brand_voice": {}, "image_provider": {},
    "notify_priority": True, "notify_mentions": True, "notify_connections": True,
    "x_client_id": "", "x_redirect_uri": "http://127.0.0.1:8787/auth/callback",
    "ai_provider": "", "chatgpt_model": "", "ai_model": "", "ai_base_url": "",
    "discovery_mode": "automatic", "daily_search_limit": 20,
    "onboarded": False, "interests": [], "theme": "dark", "notifications": False,
    "tray_enabled": False, "monitoring": False, "read_access": False, "poll_minutes": 30,
    "daily_reply_limit": 20, "daily_post_limit": 10, "daily_write_cap": 100,
    "hourly_write_limit": 10, "daily_ai_limit": 50, "same_account_limit": 3,
    "never_auto_reply": True, "require_approval": True,
    "voice": {}, "product": {}, "default_query": '("PDF editor" OR ebook) lang:en -is:retweet',
}
BOUNDS = {"social_daily_request_cap": (1,1000), "social_max_feed": (20,1000),"daily_search_limit": (1, 1000),"daily_reply_limit": (1, 1000), "daily_post_limit": (1, 1000),
          "daily_write_cap": (1, 1000), "hourly_write_limit": (1, 100),
          "daily_ai_limit": (1, 1000), "same_account_limit": (1, 20), "poll_minutes": (15, 1440)}

def get(key):
    return db.get_setting(key, DEFAULTS.get(key))

def all_settings():
    return {key: get(key) for key in DEFAULTS}

def save(values, persist=True):
    checked = {}
    for key, value in values.items():
        if key not in DEFAULTS:
            raise ValueError("Unknown setting: " + key)
        if key in ("never_auto_reply", "require_approval") and value is not True:
            raise ValueError("Approval protection cannot be disabled.")
        default = DEFAULTS[key]
        if isinstance(default, bool) and not isinstance(value, bool):
            raise ValueError(key + " must be on or off.")
        if key in BOUNDS:
            low, high = BOUNDS[key]
            if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
                raise ValueError(f"{key} must be between {low} and {high}.")
        if isinstance(default, str) and (not isinstance(value, str) or len(value) > 4000):
            raise ValueError("Invalid " + key)
        if isinstance(default, dict):
            if not isinstance(value, dict) or any(not isinstance(v, str) or len(v) > 4000 for v in value.values()):
                raise ValueError("Profile fields must be text, up to 4000 characters.")
        if key == "interests" and (not isinstance(value, list) or len(value) > 50 or any(not isinstance(x,str) or len(x)>100 for x in value)):
            raise ValueError("Enter up to 50 short interests.")
        if key == "ai_provider" and value and value not in __import__("app.ai_registry",fromlist=["CATALOG"]).CATALOG:
            raise ValueError("Choose a supported AI provider.")
        if key == "discovery_mode" and value not in {"automatic","api","web"}:
            raise ValueError("Choose Automatic, X API Search, or X Web Search.")
        if key == "theme" and value not in {"dark", "dim"}:
            raise ValueError("Choose dark or dim appearance.")
        if key == "ai_base_url" and value:
            url = urlsplit(value)
            if url.username or url.password or url.query or url.fragment:
                raise ValueError("Endpoint URLs cannot contain credentials, query parameters, or fragments.")
            if url.scheme != "https" and not (url.scheme == "http" and url.hostname in {"localhost","127.0.0.1","::1"}):
                raise ValueError("Use HTTPS, or HTTP for a local AI server.")
        if key == "x_redirect_uri":
            url = urlsplit(value)
            if url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost"} or url.path != "/auth/callback":
                raise ValueError("Use the local callback URL shown in X Connection.")
        if key in {"voice","product","brand_voice","my_profile"}:
            from .context_settings import canonical_fields
            value = canonical_fields(key,value)
        checked[key] = value
    if "ai_base_url" in checked:
        import json
        kind=checked.get("ai_provider",get("ai_provider"))
        row=db.one("SELECT config FROM ai_connections WHERE id=?",(kind,))
        if kind in {"compatible","ollama","lmstudio"} and row and store.get("ai_api_key_"+kind):
            if checked["ai_base_url"]!=json.loads(row["config"])["base_url"]:
                raise ValueError("Change an endpoint through AI Providers and re-enter its key.")
    if persist:
        import json
        reset_health=any(key in {"ai_provider","ai_model","ai_base_url"} and get(key)!=value for key,value in checked.items())
        with db.conn() as connection:
            if reset_health:checked.update(ai_health=None,ai_pause={})
            for key,value in checked.items():
                connection.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,json.dumps(value)))
    if persist and any(k in checked for k in ("ai_model","ai_base_url","chatgpt_model")):
        kind=get("ai_provider")
        row=db.one("SELECT config FROM ai_connections WHERE id=?",(kind,))
        if row:
            data=json.loads(row["config"])
            if "ai_model" in checked and kind!="chatgpt":data["model"]=checked["ai_model"]
            if "chatgpt_model" in checked and kind=="chatgpt":data["model"]=checked["chatgpt_model"]
            if "ai_base_url" in checked and kind in {"compatible","ollama","lmstudio"}:
                if checked["ai_base_url"]!=data["base_url"] and store.get("ai_api_key_"+kind):
                    # Leave credentials bound to the original endpoint; new UI verifies replacements.
                    db.set_setting("ai_base_url",data["base_url"])
                    raise ValueError("Change an endpoint through AI Providers and re-enter its key.")
                data["base_url"]=checked["ai_base_url"]
            db.execute("UPDATE ai_connections SET config=? WHERE id=?",(kind,json.dumps(data)))
            db.execute("DELETE FROM ai_model_cache WHERE connection_id=?",(kind,))


def bootstrap_dev_env():
    """Optional dev import; bundled builds never read a .env file."""
    if getattr(sys, "frozen", False) or os.getenv("XEA_TESTING"):
        return
    if db.get_setting("dev_env_imported",False):
        return
    from dotenv import dotenv_values
    values = dotenv_values(".env")
    for key in ("x_client_id","x_redirect_uri","ai_model","ai_base_url","default_query"):
        if values.get(key.upper()) and db.get_setting(key) is None:
            db.set_setting(key, values[key.upper()])
    if values.get("AI_BASE_URL") and db.get_setting("ai_provider") is None:
        db.set_setting("ai_provider", "compatible")
    if values.get("OPENAI_API_KEY") and not values.get("AI_BASE_URL") and db.get_setting("ai_provider") is None:
        db.set_setting("ai_provider","openai")
        store.set("ai_api_key_openai",values["OPENAI_API_KEY"])
    for key in PUBLIC_SECRET_NAMES:
        target = "ai_api_key_" + get("ai_provider") if key == "ai_api_key" else key
        if values.get(key.upper()) and not store.get(target):
            store.set(target, values[key.upper()])

    if values:
        db.set_setting("dev_env_imported",True)
