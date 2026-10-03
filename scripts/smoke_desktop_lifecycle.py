"""Windows native lifecycle smoke: isolated workspace, HTTP reads, normal window close.
Run with the contributor virtualenv and a built native executable. Close other app instances first.
No browser automation, social requests or paid AI generation.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import httpx

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from app.paths import VERSION
binary=Path(sys.argv[1]).resolve()
if sys.platform!="win32":raise SystemExit("This lifecycle smoke currently targets Windows.")
base="http://127.0.0.1:8787"
try:
    httpx.get(base+"/health",timeout=2)
except httpx.RequestError:
    pass
else:
    raise SystemExit("Close the current app before running an isolated desktop smoke.")

def powershell(script):
    return subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",script],
                          capture_output=True,text=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
def processes():
    result=powershell("@(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('xea-backend.exe','x-engagement-assistant.exe') } | Select-Object ProcessId,ParentProcessId,ExecutablePath) | ConvertTo-Json -Compress")
    if result.returncode:raise RuntimeError("Could not inspect native lifecycle.")
    rows=json.loads(result.stdout or '[]')
    return rows if isinstance(rows,list) else [rows]

def close(child):
    for _ in range(10):
        if child.poll() is not None:return
        result=powershell("(Get-Process -Id "+str(child.pid)+" -ErrorAction SilentlyContinue).CloseMainWindow()")
        if result.stdout.strip()=="True":return
        time.sleep(.5)
    raise RuntimeError("Could not request normal window close.")

with tempfile.TemporaryDirectory(prefix="xea-native-smoke-") as folder:
    env={**os.environ,"XEA_DATA_DIR":folder,"XEA_TESTING":"1"}
    subprocess.run([sys.executable,"-B","-c","from app import database as d; d.init_db(); d.set_setting('check_updates',False)"],env=env,cwd=ROOT,check=True)
    # Repeat to verify the runtime lock and executable are released after exit.
    for attempt in range(2):
        child=subprocess.Popen([str(binary)],env=env,creationflags=subprocess.CREATE_NO_WINDOW)
        owned={child.pid}
        try:
            with httpx.Client(base_url=base,timeout=10) as client:
                deadline=time.monotonic()+120
                while time.monotonic()<deadline:
                    if child.poll() is not None:raise RuntimeError("Native application exited during startup.")
                    try:
                        response=client.get('/health')
                        if response.is_success:break
                    except httpx.RequestError:pass
                    time.sleep(.5)
                else:raise RuntimeError("Native backend startup timed out.")
                assert response.json()['version']==VERSION
                assert client.get('/').status_code==200
                assert client.get('/api/terminal/context').status_code==200
                assert client.get('/api/dashboard').json()['today_writes']==0
                assert client.get('/api/bootstrap').json()['settings']['onboarded'] is False
            rows=processes()
            for _ in range(4):
                owned.update(row['ProcessId'] for row in rows if row['ParentProcessId'] in owned)
            assert len(owned)>=3,'Expected native app and bundled launcher/child.'
            close(child)
            assert child.wait(timeout=45)==0
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                remaining=[row for row in processes() if row['ProcessId'] in owned]
                if not remaining:break
                time.sleep(.5)
            else:raise RuntimeError('Normal close left an orphaned bundled backend.')
            print('Native launch/close cycle',attempt+1,'passed: correct version, dashboard, terminal, zero writes, no owned backend left.',flush=True)
        finally:
            # On failure clean only this test process and its previously identified descendants.
            rows=processes()
            for _ in range(4):owned.update(row['ProcessId'] for row in rows if row['ParentProcessId'] in owned)
            for row in reversed(rows):
                if row['ProcessId'] in owned and row.get('ExecutablePath') and Path(row['ExecutablePath']).parent==binary.parent:
                    powershell('Stop-Process -Id '+str(row['ProcessId'])+' -Force -ErrorAction SilentlyContinue')
            if child.poll() is None:child.wait(timeout=10)
print('Native desktop lifecycle smoke passed twice; no real account workspace was opened.',flush=True)
