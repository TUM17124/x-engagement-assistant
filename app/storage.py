"""Compatibility functions; credentials are never written to the activity database."""
import json
from . import database as db
from .secrets import store

init_db = db.init_db
conn = db.conn

def save_tokens(access_token, refresh_token, expires_at):
    store.set("oauth_tokens", json.dumps({"access_token": access_token, "refresh_token": refresh_token, "expires_at": expires_at}))

def load_tokens():
    raw = store.get("oauth_tokens")
    return json.loads(raw) if raw else None

def clear_tokens():
    store.delete("oauth_tokens")
    db.set_setting("x_profile", None)

def log_action(action_type, text, target_id=None,platform='x'):
    db.execute("INSERT INTO actions(action_type,target_id,text,created_at,platform) VALUES(?,?,?,?,?)",
               (action_type, target_id, text, db.now(),platform))

def action_count_today():
    return db.one("SELECT COUNT(*) n FROM actions WHERE substr(created_at,1,10)=?", (db.now()[:10],))["n"]

def duplicate_recent(text):
    return bool(db.one("SELECT 1 FROM actions WHERE text=? LIMIT 1", (text.strip(),)))

def recent_actions(limit=30):
    return db.rows("SELECT * FROM actions ORDER BY id DESC LIMIT ?", (limit,))
