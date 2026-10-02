"""Launch the real native window against isolated data; no browser automation or external calls."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import sys
import time
import httpx
from PIL import ImageGrab

root=Path(__file__).resolve().parent.parent
workspace=root/".tools"/"desktop-smoke"
workspace.mkdir(parents=True,exist_ok=True)
os.environ["XEA_DATA_DIR"]=str(workspace)
os.environ["XEA_TESTING"]="1"
sys.path.insert(0,str(root))
from app import database as db
db.init_db()
db.set_setting("onboarded",True)
db.set_setting("tray_enabled",False)
db.set_setting("monitoring",False)
db.set_setting("assistant_mode",False)
db.set_setting("automations_paused",True)
binary=Path(sys.argv[1]).resolve()
user=ctypes.WinDLL("user32",use_last_error=True)
user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
user.IsWindowVisible.argtypes=[wintypes.HWND]
user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
CALLBACK=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
window=None
child=subprocess.Popen([str(binary)],env=os.environ.copy(),creationflags=subprocess.CREATE_NO_WINDOW)
try:
    with httpx.Client(base_url="http://127.0.0.1:8787",timeout=3) as client:
        for _ in range(90):
            if child.poll() is not None:raise RuntimeError("Desktop exited during startup.")
            try:
                if client.get("/health").status_code==200:break
            except httpx.RequestError:pass
            time.sleep(1)
        else:raise RuntimeError("Desktop backend did not become ready.")
        boot=client.get("/api/bootstrap").json()
        assert boot["settings"]["onboarded"]
        client.headers["X-CSRF-Token"]=boot["csrf"]
        assert client.get("/").status_code==200
        assert client.get("/api/chatgpt/status").json()["connected"] is False
        assert client.get("/api/dashboard").json()["today_writes"]==0
        reply=client.post("/api/terminal/run",json={"text":"status","timezone":"Africa/Nairobi"})
        assert reply.status_code==200 and '"type": "done"' in reply.text
        windows=[]
        @CALLBACK
        def collect(hwnd,_):
            pid=wintypes.DWORD()
            user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
            if pid.value==child.pid and user.IsWindowVisible(hwnd):windows.append(hwnd)
            return True
        time.sleep(4)
        user.EnumWindows(collect,0)
        if not windows:raise RuntimeError("The native app has no visible window.")
        window=windows[0]
        screenshot=root/"artifacts"/"desktop-home.png"
        screenshot.parent.mkdir(exist_ok=True)
        ImageGrab.grab(window=window).save(screenshot)
        print("Native window, bundled backend, dashboard, terminal and zero writes verified.")
        print("Screenshot:",screenshot)
        user.PostMessageW(window,0x0010,0,0)
        child.wait(timeout=20)
        time.sleep(1)
        try:client.get("/health")
        except httpx.RequestError:print("Desktop close stopped its backend.")
        else:raise RuntimeError("Backend remained after closing the app.")
finally:
    if child.poll() is None:
        if window:user.PostMessageW(window,0x0010,0,0)
        try:child.wait(timeout=10)
        except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=10)
