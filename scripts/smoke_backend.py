"""Launch a packaged backend with isolated data; HTTP-only verification, no external calls."""
import os
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import httpx

binary=Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory() as folder:
    env={**os.environ,"XEA_DATA_DIR":folder,"XEA_DESKTOP_TOKEN":"isolated-smoke-control","XEA_TESTING":"1"}
    # Disable public release polling in this isolated smoke workspace before launch.
    subprocess.run([sys.executable,"-c","from app import database as d; d.init_db(); d.set_setting('check_updates',False)"],env=env,check=True,cwd=Path(__file__).resolve().parent.parent)
    child=subprocess.Popen([str(binary),"--port","18787"],env=env,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    try:
        with httpx.Client(base_url="http://127.0.0.1:18787",timeout=3) as client:
            for _ in range(90):
                if child.poll() is not None:
                    raise RuntimeError("Packaged backend exited during startup.")
                try:
                    if client.get("/health").status_code==200:break
                except httpx.RequestError:
                    pass
                time.sleep(1)
            else:raise RuntimeError("Packaged backend did not start.")
            root=client.get("/")
            assert root.status_code==200 and "Multi-Social AI Engagement Command Center" in root.text
            boot=client.get("/api/bootstrap").json()
            assert not boot["settings"]["onboarded"]
            assert boot["settings"]["ai_provider"]==""
            client.headers["X-CSRF-Token"]=boot["csrf"]
            assert len(client.get("/api/ai/providers").json()["providers"])>=11
            assert client.get("/api/trend-radar").json()["items"]==[]
            assert client.put("/api/settings",json={"ai_provider":"gemini"}).status_code==200
            profile={"name":"Isolated packaged test","role":"Founder","bio":"","industry":"Software","expertise":"Coding","products":"Local app","audience":"Creators","goals":"Useful conversations"}
            assert client.put("/api/profile",json=profile).json()==profile
            assert client.get("/api/profile").json()==profile
            assert client.put("/api/profile",json={"name":7}).status_code==422
            assert client.get("/static/forms.js").status_code==200
            assert client.get("/static/terminal.js").status_code==200
            assert "function updatesPage" in client.get("/static/updates.js").text
            update=client.get("/api/updates").json()
            assert update["settings"]["check_updates"] is False
            assert "blogtrottr.com" in update["email_signup_url"]
            assert client.get("/api/chatgpt/status").json()["connected"] is False
            command=client.post("/api/terminal/run",json={"text":"set profile name to Packaged name","timezone":"UTC"})
            events=[json.loads(line[6:]) for line in command.text.splitlines() if line.startswith("data: ")]
            approval=next(e["request"] for e in events if e["type"]=="approval")
            confirmed=client.post("/api/terminal/approvals/"+approval["id"]+"/confirm",json={"checksum":approval["checksum"],"confirmed":True})
            assert confirmed.status_code==200
            assert client.get("/api/profile").json()["name"]=="Packaged name"
            assert client.get("/api/profile").json()["role"]=="Founder"
            command=client.post("/api/terminal/run",json={"text":"status","timezone":"UTC"})
            assert command.status_code==200 and '"type": "done"' in command.text
            assert client.get("/api/terminal/automations").json()["items"]==[]
            assert client.get("/static/social.js").status_code==200
            assert len(client.get("/api/social/accounts").json())==7
            assert client.get("/api/social/trends").json()==[]
            assert client.get("/api/media").json()==[]
            parsed=client.get("/parse-tweet-url",params={"tweet_url":"https://x.com/demo/status/123456789"}).json()
            assert parsed["tweet_id"]=="123456789"
            assert client.get("/parse-tweet-url",params={"tweet_url":"bad"}).status_code==400
            assert client.put("/api/settings",json={"theme":"dim"}).status_code==200
            assert client.put("/api/secrets/ai_api_key",json={"value":"isolated-smoke-key"}).status_code==200
            assert "isolated-smoke-key" not in client.get("/api/settings").text
            assert client.post("/api/onboarding/finish").status_code==200
            assert client.get("/api/dashboard").json()["today_writes"]==0
            print("Packaged runtime smoke passed: launch, dashboard, AI terminal/status, neutral AI selection, automation storage, UI assets, onboarding, settings, secure secret roundtrip, URL parsing, zero writes.")
            client.post("/desktop/shutdown",headers={"X-Desktop-Token":"isolated-smoke-control"})
            child.wait(timeout=15)
            child=subprocess.Popen([str(binary),"--port","18787"],env=env,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            for _ in range(45):
                try:
                    if client.get("/health").status_code==200:break
                except httpx.RequestError:pass
                time.sleep(1)
            else:raise RuntimeError("Packaged backend did not restart.")
            assert client.get("/api/profile").json()["name"]=="Packaged name"
            assert client.get("/api/profile").json()["role"]=="Founder"
            print("Profile persistence verified after a real packaged-process restart.")
            client.post("/desktop/shutdown",headers={"X-Desktop-Token":"isolated-smoke-control"})
            child.wait(timeout=15)
    finally:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=15)
