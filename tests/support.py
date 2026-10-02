import os
import tempfile
from pathlib import Path
from contextlib import ExitStack
from unittest import TestCase
from unittest.mock import patch,AsyncMock

os.environ["XEA_TESTING"]="1"
# Import the app against a memory-only test vault. Production has no plaintext fallback.
from app import secrets as secret_module
class MemoryStore:
    def __init__(self): self.values={}
    def get(self,k): return self.values.get(k,"")
    def set(self,k,v): self.values[k]=v
    def delete(self,k): self.values.pop(k,None)
    def masked(self,k):
        v=self.get(k)
        return "????????"+v[-4:] if len(v)>4 else ("????" if v else "")
vault=MemoryStore()
secret_module.store=vault
from app import main,database as db,preferences as prefs,workspace as ws,storage,x_api
import httpx
from fastapi.testclient import TestClient

class AppTest(TestCase):
    def setUp(self):
        self.stack=ExitStack()
        self.addCleanup(self.stack.close)
        directory=self.stack.enter_context(tempfile.TemporaryDirectory())
        self.stack.enter_context(patch.object(db,"DB_PATH",Path(directory)/"test.sqlite3"))
        vault.values.clear()
        self.network=self.stack.enter_context(patch.object(httpx.AsyncClient,"send",side_effect=AssertionError("Real network is forbidden in tests")))
        self.stack.enter_context(patch("app.workers.run_workers",new_callable=AsyncMock))
        self.client=self.stack.enter_context(TestClient(main.app))
        prefs.save({"ai_provider":"gemini","ai_model":"gemini-2.5-flash"})
        token=self.client.get("/api/bootstrap").json()["csrf"]
        self.client.headers["X-CSRF-Token"]=token

    def post(self,url,body=None):
        return self.client.post(url,json=body if body is not None else {})

    def source(self):
        r=self.post("/api/feed/import",{"tweet_url":"https://x.com/test_user/status/1234567890123456789",
                                      "text":"How do you organize PDF annotations?"})
        self.assertEqual(r.status_code,200,r.text)
        return r.json()

    def draft(self,kind="original",text="A useful original idea.",feed_id=None):
        return self.post("/api/drafts",{"kind":kind,"text":text,"feed_id":feed_id}).json()
