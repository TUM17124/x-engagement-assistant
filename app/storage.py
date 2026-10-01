import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent.parent / "engagement.db"

@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        with c:
            yield c
    finally:
        c.close()

def init_db():
    with conn() as c:
        c.execute('''
            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                expires_at INTEGER
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                target_id TEXT,
                text TEXT,
                created_at TEXT NOT NULL
            )
        ''')

def save_tokens(access_token: str, refresh_token: str | None, expires_at: int | None):
    with conn() as c:
        c.execute(
            '''INSERT INTO tokens(id, access_token, refresh_token, expires_at)
               VALUES(1, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 access_token=excluded.access_token,
                 refresh_token=excluded.refresh_token,
                 expires_at=excluded.expires_at''',
            (access_token, refresh_token, expires_at),
        )

def load_tokens():
    with conn() as c:
        row = c.execute("SELECT * FROM tokens WHERE id=1").fetchone()
        return dict(row) if row else None

def clear_tokens():
    with conn() as c:
        c.execute("DELETE FROM tokens WHERE id=1")

def log_action(action_type: str, text: str, target_id: str | None = None):
    with conn() as c:
        c.execute(
            "INSERT INTO actions(action_type, target_id, text, created_at) VALUES (?, ?, ?, ?)",
            (action_type, target_id, text, datetime.now(timezone.utc).isoformat()),
        )

def action_count_today():
    today = datetime.now(timezone.utc).date().isoformat()
    with conn() as c:
        row = c.execute(
            "SELECT COUNT(*) AS n FROM actions WHERE substr(created_at,1,10)=?",
            (today,),
        ).fetchone()
        return int(row["n"])

def duplicate_recent(text: str):
    with conn() as c:
        row = c.execute(
            "SELECT 1 FROM actions WHERE text=? ORDER BY id DESC LIMIT 1",
            (text.strip(),),
        ).fetchone()
        return bool(row)

def recent_actions(limit: int = 30):
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM actions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
