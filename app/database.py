"""Versioned local schema. Connections are short-lived and transactions explicit."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from .paths import data_dir

DB_PATH = data_dir() / "workspace.sqlite3"
SCHEMA_VERSION = 4
MIGRATIONS = [
"""
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS actions (id INTEGER PRIMARY KEY AUTOINCREMENT, action_type TEXT NOT NULL,
 target_id TEXT, text TEXT, created_at TEXT NOT NULL);
CREATE TABLE watched_accounts (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
 enabled INTEGER NOT NULL DEFAULT 1, priority TEXT NOT NULL DEFAULT 'Normal', topics TEXT NOT NULL DEFAULT '',
 ai_drafting INTEGER NOT NULL DEFAULT 0, notifications INTEGER NOT NULL DEFAULT 0,
 last_seen_id TEXT, next_poll_at TEXT, error TEXT NOT NULL DEFAULT '');
CREATE TABLE tracked_topics (id INTEGER PRIMARY KEY, name TEXT NOT NULL, keywords TEXT NOT NULL,
 excluded TEXT NOT NULL DEFAULT '', languages TEXT NOT NULL DEFAULT 'en', enabled INTEGER NOT NULL DEFAULT 1,
 priority TEXT NOT NULL DEFAULT 'Normal', query TEXT NOT NULL DEFAULT '', next_poll_at TEXT, error TEXT NOT NULL DEFAULT '');
CREATE TABLE feed_items (id TEXT PRIMARY KEY, username TEXT NOT NULL, display_name TEXT NOT NULL DEFAULT '',
 avatar TEXT NOT NULL DEFAULT '', text TEXT NOT NULL, posted_at TEXT, imported_at TEXT NOT NULL,
 source TEXT NOT NULL, topic TEXT NOT NULL DEFAULT '', metrics TEXT NOT NULL DEFAULT '{}',
 saved INTEGER NOT NULL DEFAULT 0, ignored INTEGER NOT NULL DEFAULT 0);
CREATE TABLE drafts (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, feed_id TEXT, text TEXT NOT NULL,
 generated_text TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'draft', reason TEXT NOT NULL DEFAULT '',
 score INTEGER NOT NULL DEFAULT 0, topic TEXT NOT NULL DEFAULT '', provider TEXT NOT NULL DEFAULT '',
 model TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE approved_content (draft_id INTEGER PRIMARY KEY, content_hash TEXT NOT NULL, approved_at TEXT NOT NULL);
CREATE TABLE scheduled_posts (id INTEGER PRIMARY KEY, draft_id INTEGER NOT NULL UNIQUE, content_hash TEXT NOT NULL,
 due_at TEXT NOT NULL, timezone TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', error TEXT NOT NULL DEFAULT '',
 notified INTEGER NOT NULL DEFAULT 0);
CREATE TABLE activity (id INTEGER PRIMARY KEY, action TEXT NOT NULL, timestamp TEXT NOT NULL,
 draft_id INTEGER, post_id TEXT, target_account TEXT NOT NULL DEFAULT '', generated_text TEXT NOT NULL DEFAULT '',
 final_text TEXT NOT NULL DEFAULT '', provider TEXT NOT NULL DEFAULT '', model TEXT NOT NULL DEFAULT '',
 channel TEXT NOT NULL DEFAULT 'local', status TEXT NOT NULL, error TEXT NOT NULL DEFAULT '', topic TEXT NOT NULL DEFAULT '');
CREATE TABLE muted_accounts (username TEXT PRIMARY KEY);
CREATE TABLE muted_topics (topic TEXT PRIMARY KEY);
CREATE TABLE notifications (id INTEGER PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL, delivered INTEGER NOT NULL DEFAULT 0);
CREATE INDEX activity_time ON activity(timestamp);
CREATE INDEX draft_status ON drafts(status);
CREATE INDEX scheduled_due ON scheduled_posts(status, due_at);
""",
"""
CREATE TABLE ai_usage (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL);
CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
""",
"""
CREATE INDEX feed_time ON feed_items(imported_at);
CREATE INDEX activity_target ON activity(target_account, timestamp);
"""
]

MIGRATIONS.append("CREATE TABLE search_usage (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, retrieved INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL);")

def now():
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=15000")
    try:
        with connection:
            yield connection
    finally:
        connection.close()

def init_db():
    with conn() as c:
        version = c.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise RuntimeError("This database belongs to a newer application version.")
        for index in range(version, SCHEMA_VERSION):
            c.executescript("BEGIN IMMEDIATE;\n" + MIGRATIONS[index] +
                            f"\nPRAGMA user_version={index + 1};\nCOMMIT;")
        # Migrate the previous developer application's token table if importing an old DB.
        exists = c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='tokens'").fetchone()
        if exists:
            from .secrets import store
            row = c.execute("SELECT * FROM tokens WHERE id=1").fetchone()
            if row:
                store.set("oauth_tokens", json.dumps(dict(row)))
            c.execute("PRAGMA secure_delete=ON")
            c.execute("DROP TABLE tokens")
    if exists:
        with conn() as c:
            c.execute("VACUUM")

def rows(sql, args=()):
    with conn() as c:
        return [dict(row) for row in c.execute(sql, args).fetchall()]

def one(sql, args=()):
    result = rows(sql, args)
    return result[0] if result else None

def execute(sql, args=()):
    with conn() as c:
        return c.execute(sql, args).lastrowid

def get_setting(key, default=None):
    if not DB_PATH.exists():
        return default
    try:
        row = one("SELECT value FROM settings WHERE key=?", (key,))
        return json.loads(row["value"]) if row else default
    except sqlite3.OperationalError:
        return default

def set_setting(key, value):
    execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value)))
