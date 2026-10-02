"""Use the maintainer's OS-protected signing credentials without printing them."""
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from app.secrets import SecretStore
folder=Path(os.environ.get("LOCALAPPDATA",Path.home()))/"SocialCommandReleaseSigning"
key=folder/"updater.key"
password=SecretStore(folder/"vault").get("signing_password")
if not key.exists() or not password: raise SystemExit("Run scripts/setup_update_key.py once on the release maintainer's computer.")
env={**os.environ,"TAURI_SIGNING_PRIVATE_KEY":str(key),"TAURI_SIGNING_PRIVATE_KEY_PASSWORD":password}
raise SystemExit(subprocess.call(["node",str(ROOT/"node_modules/@tauri-apps/cli/tauri.js"),"build"],cwd=ROOT,env=env))
