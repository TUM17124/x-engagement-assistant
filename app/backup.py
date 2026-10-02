"""Portable backups exclude the OS secret store and never restore approvals."""
import json
import sqlite3
import tempfile
from pathlib import Path
from . import database as db, preferences as prefs

TABLES=["watched_accounts","tracked_topics","feed_items","drafts","activity","actions","muted_accounts","muted_topics","scheduled_posts"]
EXTRA_TABLES=["social_watch","social_mutes","ideas","media","media_usage","terminal_commands","action_requests","automations","automation_runs","automation_steps","command_events","application_memory"]

def backup_bytes():
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/"backup.sqlite3"
        with db.conn() as source:
            target=sqlite3.connect(path)
            try:
                source.backup(target)
                # Cached account metadata is not a secret; operational/health state is not portable.
                allowed=list(prefs.DEFAULTS)
                target.execute("DELETE FROM settings WHERE key NOT IN ("+",".join("?" for _ in allowed)+")",allowed)
                target.execute("DELETE FROM app_meta")
                target.execute("DELETE FROM notifications")
                target.commit()
            finally:
                target.close()
        return path.read_bytes()

def restore_bytes(data):
    if not data.startswith(b"SQLite format 3\x00"):
        raise ValueError("Choose a valid SQLite workspace backup.")
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/"restore.sqlite3"
        path.write_bytes(data)
        source=sqlite3.connect(path.as_uri()+"?mode=ro",uri=True)
        source.row_factory=sqlite3.Row
        try:
            source.execute("PRAGMA trusted_schema=OFF")
            if source.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                raise ValueError("The backup failed its integrity check.")
            version=source.execute("PRAGMA user_version").fetchone()[0]
            if version<1 or version>db.SCHEMA_VERSION:
                raise ValueError("Use a backup created by a compatible desktop version.")
            tables={r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not set(TABLES).issubset(tables):
                raise ValueError("This is not a complete X Engagement Assistant backup.")
            # Validate first; copy rows into OUR schema, never execute imported SQL/triggers.
            copied={table:[dict(r) for r in source.execute("SELECT * FROM "+table)] for table in TABLES+EXTRA_TABLES if table in tables}
            settings={r["key"]:json.loads(r["value"]) for r in source.execute("SELECT * FROM settings") if r["key"] in prefs.DEFAULTS}
            # Validate through an isolated checker without changing live preferences.
            prefs.save(settings, persist=False)
            with db.conn() as target:
                target.execute("DELETE FROM approved_content")
                for table in reversed(TABLES+EXTRA_TABLES):
                    target.execute("DELETE FROM "+table)
                for table in TABLES+EXTRA_TABLES:
                    valid_columns=[r[1] for r in target.execute("PRAGMA table_info("+table+")")]
                    for row in copied.get(table,[]):
                        columns=[k for k in valid_columns if k in row]
                        if table=="automations":
                            row["status"]="paused";row["error"]="Restored automation needs explicit review and resume."
                        if table=="action_requests":
                            row["status"]="rejected";row["error"]="Restored action requires a fresh request."
                        if table=="terminal_commands" and row["status"]=="running":row["status"]="interrupted"
                        if table=="drafts":
                            row["status"]="draft"
                        if table=="scheduled_posts":
                            row["status"]="cancelled";row["error"]="Restored schedule requires a new approval."
                        target.execute("INSERT INTO "+table+" ("+",".join(columns)+") VALUES("+",".join("?" for _ in columns)+")",
                                       [row[k] for k in columns])
                for key,value in settings.items():
                    if key in {"monitoring","assistant_mode","onboarded"}:
                        continue
                    target.execute("INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,json.dumps(value)))
                target.execute("UPDATE settings SET value='false' WHERE key IN ('monitoring','assistant_mode')")
        except sqlite3.Error:
            raise ValueError("The backup is invalid or incompatible. Your workspace was not replaced.") from None
        finally:
            source.close()
