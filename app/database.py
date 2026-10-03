"""Versioned local schema. Connections are short-lived and transactions explicit."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from .paths import data_dir

DB_PATH = data_dir() / "workspace.sqlite3"
SCHEMA_VERSION = 10
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

MIGRATIONS.append("""
ALTER TABLE feed_items ADD COLUMN platform TEXT NOT NULL DEFAULT 'x';
ALTER TABLE feed_items ADD COLUMN external_id TEXT NOT NULL DEFAULT '';
ALTER TABLE feed_items ADD COLUMN url TEXT NOT NULL DEFAULT '';
ALTER TABLE feed_items ADD COLUMN content_kind TEXT NOT NULL DEFAULT 'post';
ALTER TABLE feed_items ADD COLUMN priority INTEGER NOT NULL DEFAULT 0;
ALTER TABLE feed_items ADD COLUMN reason TEXT NOT NULL DEFAULT '';
ALTER TABLE feed_items ADD COLUMN analyzed INTEGER NOT NULL DEFAULT 0;
ALTER TABLE feed_items ADD COLUMN media_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE drafts ADD COLUMN platform TEXT NOT NULL DEFAULT 'x';
ALTER TABLE drafts ADD COLUMN account_id TEXT NOT NULL DEFAULT '';
ALTER TABLE drafts ADD COLUMN media_ids TEXT NOT NULL DEFAULT '[]';
ALTER TABLE drafts ADD COLUMN quality TEXT NOT NULL DEFAULT '[]';
ALTER TABLE activity ADD COLUMN platform TEXT NOT NULL DEFAULT 'x';
ALTER TABLE scheduled_posts ADD COLUMN delivery TEXT NOT NULL DEFAULT 'api';
CREATE TABLE social_accounts(platform TEXT PRIMARY KEY,account_id TEXT NOT NULL,name TEXT NOT NULL,
 avatar TEXT NOT NULL DEFAULT '',permissions TEXT NOT NULL DEFAULT '',last_sync TEXT,api_status TEXT NOT NULL DEFAULT '');
CREATE TABLE social_usage(id INTEGER PRIMARY KEY,platform TEXT NOT NULL,operation TEXT NOT NULL,created_at TEXT NOT NULL,status TEXT NOT NULL);
CREATE TABLE social_watch(id INTEGER PRIMARY KEY,platform TEXT NOT NULL,handle TEXT NOT NULL,url TEXT NOT NULL,
 category TEXT NOT NULL DEFAULT 'favorite',priority TEXT NOT NULL DEFAULT 'Normal',topics TEXT NOT NULL DEFAULT '',
 enabled INTEGER NOT NULL DEFAULT 1,notifications INTEGER NOT NULL DEFAULT 0,auto_draft INTEGER NOT NULL DEFAULT 0,
 last_checked TEXT,next_check TEXT,last_seen_id TEXT,error TEXT NOT NULL DEFAULT '',UNIQUE(platform,handle,category));
CREATE TABLE social_mutes(platform TEXT NOT NULL,author TEXT NOT NULL,PRIMARY KEY(platform,author));
CREATE TABLE ideas(id INTEGER PRIMARY KEY,title TEXT NOT NULL,text TEXT NOT NULL,url TEXT NOT NULL DEFAULT '',
 kind TEXT NOT NULL DEFAULT 'thought',created_at TEXT NOT NULL);
CREATE TABLE media(id TEXT PRIMARY KEY,name TEXT NOT NULL,mime TEXT NOT NULL,size INTEGER NOT NULL,width INTEGER,height INTEGER,
 created_at TEXT NOT NULL,tags TEXT NOT NULL DEFAULT '',folder TEXT NOT NULL DEFAULT '',favorite INTEGER NOT NULL DEFAULT 0,
 caption TEXT NOT NULL DEFAULT '',alt_text TEXT NOT NULL DEFAULT '',parent_id TEXT);
CREATE TABLE media_usage(id INTEGER PRIMARY KEY,media_id TEXT NOT NULL,draft_id INTEGER NOT NULL,used_at TEXT NOT NULL);
CREATE INDEX social_feed_platform ON feed_items(platform,imported_at);
CREATE INDEX social_usage_date ON social_usage(platform,created_at);
""")

MIGRATIONS.append("ALTER TABLE actions ADD COLUMN platform TEXT NOT NULL DEFAULT 'x'; DELETE FROM approved_content; UPDATE drafts SET status='draft' WHERE status IN ('approved','scheduled'); UPDATE scheduled_posts SET status='cancelled',error='Reapprove after the multi-social upgrade.' WHERE status='pending';")

MIGRATIONS.append("""
CREATE TABLE terminal_commands(id TEXT PRIMARY KEY,source TEXT NOT NULL,raw_input TEXT NOT NULL,
 parsed_intent TEXT NOT NULL DEFAULT '',arguments TEXT NOT NULL DEFAULT '{}',risk_level TEXT NOT NULL DEFAULT 'READ_ONLY',
 requires_approval INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL,created_at TEXT NOT NULL,
 finished_at TEXT,result TEXT NOT NULL DEFAULT '{}');
CREATE TABLE action_requests(id TEXT PRIMARY KEY,command_id TEXT,tool TEXT NOT NULL,arguments TEXT NOT NULL,
 snapshot TEXT NOT NULL,checksum TEXT NOT NULL,risk TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',
 created_at TEXT NOT NULL,finished_at TEXT,error TEXT NOT NULL DEFAULT '');
CREATE TABLE automations(id INTEGER PRIMARY KEY,name TEXT NOT NULL,trigger TEXT NOT NULL,config TEXT NOT NULL,
 timezone TEXT NOT NULL,status TEXT NOT NULL,next_run TEXT NOT NULL,created_at TEXT NOT NULL,error TEXT NOT NULL DEFAULT '');
CREATE TABLE automation_runs(id INTEGER PRIMARY KEY,automation_id INTEGER NOT NULL,started_at TEXT NOT NULL,
 finished_at TEXT,status TEXT NOT NULL,summary TEXT NOT NULL DEFAULT '',UNIQUE(automation_id,started_at));
CREATE TABLE automation_steps(run_id INTEGER NOT NULL,step_key TEXT NOT NULL,status TEXT NOT NULL,
 result TEXT NOT NULL DEFAULT '{}',PRIMARY KEY(run_id,step_key));
CREATE TABLE command_events(id INTEGER PRIMARY KEY,command_id TEXT,automation_id INTEGER,event TEXT NOT NULL,
 tool TEXT NOT NULL DEFAULT '',status TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE application_memory(key TEXT PRIMARY KEY,value TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE INDEX automation_next ON automations(status,next_run);
CREATE INDEX action_requests_status ON action_requests(status,created_at);
CREATE INDEX terminal_time ON terminal_commands(created_at);
-- Preserve configured providers; older default-Gemini installations without saved settings keep their provider.
INSERT OR IGNORE INTO settings(key,value)
 SELECT 'ai_provider','"gemini"' WHERE EXISTS(SELECT 1 FROM settings);
""")

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

MIGRATIONS.append("""
CREATE TABLE ai_connections (id TEXT PRIMARY KEY, config TEXT NOT NULL, health TEXT NOT NULL DEFAULT '{}');
CREATE TABLE ai_model_cache (connection_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, fetched_at REAL NOT NULL, models TEXT NOT NULL);
CREATE TABLE ai_requests (id INTEGER PRIMARY KEY, provider TEXT NOT NULL, model TEXT NOT NULL, feature TEXT NOT NULL,
 created_at TEXT NOT NULL, duration_ms INTEGER NOT NULL, input_tokens INTEGER, output_tokens INTEGER,
 status TEXT NOT NULL, finish_reason TEXT NOT NULL DEFAULT '', request_id TEXT NOT NULL DEFAULT '', prompt TEXT);
""")

MIGRATIONS.append("""
CREATE TABLE trend_items(id TEXT PRIMARY KEY,source TEXT NOT NULL,data TEXT NOT NULL,observed_at TEXT NOT NULL,
 saved INTEGER NOT NULL DEFAULT 0,ignored INTEGER NOT NULL DEFAULT 0);
CREATE TABLE trend_sources(source TEXT PRIMARY KEY,fetched_at TEXT NOT NULL DEFAULT '',next_fetch REAL NOT NULL DEFAULT 0,error TEXT NOT NULL DEFAULT '');
CREATE INDEX trend_observed ON trend_items(observed_at);
""")

MIGRATIONS.append("""
CREATE TABLE video_jobs(id TEXT PRIMARY KEY,provider TEXT NOT NULL,model TEXT NOT NULL,prompt TEXT NOT NULL,
 fingerprint TEXT NOT NULL,remote_id TEXT NOT NULL DEFAULT '',status TEXT NOT NULL,created_at TEXT NOT NULL,
 next_poll REAL NOT NULL DEFAULT 0,media_id TEXT NOT NULL DEFAULT '',error TEXT NOT NULL DEFAULT '');
CREATE INDEX video_fingerprint ON video_jobs(fingerprint);
""")

def init_db():
    with conn() as c:
        version = c.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise RuntimeError("This database belongs to a newer application version.")
        if 0 < version < SCHEMA_VERSION:
            backup = DB_PATH.with_name("before-schema-" + str(SCHEMA_VERSION) + ".sqlite3")
            if not backup.exists():
                with sqlite3.connect(backup) as target: c.backup(target)
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
