"""Explicit migration from the original developer database; never copy plaintext tokens into SQLite."""
import json
import sqlite3
import tempfile
from pathlib import Path
from . import database as db
from .storage import save_tokens
from .secrets import store

def import_legacy(data):
    if not data.startswith(b"SQLite format 3\x00"):
        raise ValueError("Choose the original engagement.db file.")
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/"legacy.db"
        path.write_bytes(data)
        source=sqlite3.connect(path.as_uri()+"?mode=ro",uri=True)
        source.row_factory=sqlite3.Row
        try:
            source.execute("PRAGMA trusted_schema=OFF")
            if source.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                raise ValueError("Legacy database integrity check failed.")
            tables={r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "actions" not in tables:
                raise ValueError("This is not the original engagement database.")
            actions=[dict(r) for r in source.execute("SELECT * FROM actions")]
            token=source.execute("SELECT * FROM tokens WHERE id=1").fetchone() if "tokens" in tables else None
            if token and not store.get("oauth_tokens"):
                save_tokens(token["access_token"],token["refresh_token"],token["expires_at"])
            imported=0
            with db.conn() as c:
                for row in actions:
                    if row["action_type"] not in {"post","reply","quote"}:
                        continue
                    exists=c.execute("SELECT 1 FROM actions WHERE action_type=? AND text=? AND created_at=?",
                                     (row["action_type"],row["text"],row["created_at"])).fetchone()
                    if exists:continue
                    c.execute("INSERT INTO actions(action_type,target_id,text,created_at) VALUES(?,?,?,?)",
                              (row["action_type"],row.get("target_id"),row["text"],row["created_at"]))
                    c.execute("INSERT INTO activity(action,timestamp,post_id,final_text,channel,status) VALUES(?,?,?,?,?,?)",
                              (row["action_type"],row["created_at"],row.get("target_id") if row["action_type"]=="post" else None,row["text"],"API","published"))
                    imported+=1
            return {"imported":imported,"note":"History and available login tokens migrated. The original file is unchanged and may still contain old plaintext tokens; keep it private or remove it after confirming migration."}
        except sqlite3.Error:
            raise ValueError("The legacy database is invalid or incompatible.") from None
        finally:
            source.close()
