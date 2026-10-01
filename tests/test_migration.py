import asyncio
import sqlite3
from pathlib import Path
import tempfile
from unittest.mock import patch,AsyncMock
from support import AppTest,db,prefs,ws,x_api,vault
from app.legacy import import_legacy

class MigrationTests(AppTest):
    def test_legacy_history_and_tokens_migrate_without_plaintext(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"old.db"
            source=sqlite3.connect(path)
            source.executescript("CREATE TABLE tokens(id INTEGER PRIMARY KEY,access_token TEXT,refresh_token TEXT,expires_at INTEGER); CREATE TABLE actions(id INTEGER PRIMARY KEY,action_type TEXT,target_id TEXT,text TEXT,created_at TEXT);")
            source.execute("INSERT INTO tokens VALUES(1,?,?,?)",("legacy-access-private","legacy-refresh-private",9999999999))
            source.execute("INSERT INTO actions VALUES(1,'post','123','A historical post','2026-01-01T00:00:00+00:00')")
            source.commit();source.close()
            data=path.read_bytes()
            self.assertEqual(import_legacy(data)["imported"],1)
            self.assertEqual(import_legacy(data)["imported"],0)
        self.assertIn("legacy-access-private",vault.get("oauth_tokens"))
        self.assertNotIn(b"legacy-access-private",db.DB_PATH.read_bytes())
        self.assertEqual(db.one("SELECT COUNT(*) n FROM actions")["n"],1)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM activity")["n"],1)

    def test_existing_login_is_not_overwritten_by_import(self):
        vault.set("oauth_tokens","current")
        with self.assertRaises(ValueError):import_legacy(b"invalid")
        self.assertEqual(vault.get("oauth_tokens"),"current")

    def test_concurrent_publish_is_single_send(self):
        draft=ws.save_draft("original","Concurrency-safe content")
        ws.approve(draft["id"])
        async def run():
            async def send(text):
                await asyncio.sleep(.02)
                return {"data":{"id":"123"}}
            with patch.object(x_api,"create_post",new_callable=AsyncMock,side_effect=send) as post:
                results=await asyncio.gather(ws.publish(draft["id"]),ws.publish(draft["id"]),return_exceptions=True)
                self.assertEqual(post.await_count,1)
                self.assertEqual(sum(isinstance(r,ValueError) for r in results),1)
        asyncio.run(run())
