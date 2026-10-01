"""Run with the build virtualenv Python; packages Python and dependencies for end users."""
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent.parent
os.chdir(ROOT)
target=os.environ.get("TAURI_ENV_TARGET_TRIPLE","x86_64-pc-windows-msvc" if sys.platform=="win32" else "")
if not target:
    raise SystemExit("Set TAURI_ENV_TARGET_TRIPLE for this platform.")
subprocess.run([sys.executable,"-m","PyInstaller","--noconfirm","--clean","--onefile","--noconsole",
    "--name","xea-backend","--paths",str(ROOT),
    "--add-data",f"{ROOT/'app/templates'}{os.pathsep}app/templates",
    "--add-data",f"{ROOT/'app/static'}{os.pathsep}app/static",
    "--collect-submodules","app","--collect-submodules","keyring.backends",
    "--collect-data","certifi","--collect-data","tzdata",
    "--hidden-import","uvicorn.logging","--hidden-import","uvicorn.loops.auto",
    "--hidden-import","uvicorn.protocols.http.auto","--hidden-import","uvicorn.protocols.websockets.auto",
    "--hidden-import","uvicorn.lifespan.on","app/desktop_entry.py"],check=True)
out=ROOT/"src-tauri/binaries"
out.mkdir(exist_ok=True)
extension=".exe" if sys.platform=="win32" else ""
import shutil
shutil.copy2(ROOT/"dist"/("xea-backend"+extension),out/("xea-backend-"+target+extension))
print("Bundled backend:",out/("xea-backend-"+target+extension))
