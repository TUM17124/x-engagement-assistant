"""Maintainer-only: generate an encrypted signing key outside the repository."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from app.secrets import SecretStore
folder=Path(os.environ.get("LOCALAPPDATA",Path.home()))/"SocialCommandReleaseSigning"
folder.mkdir(parents=True,exist_ok=True)
key=folder/"updater.key"
vault=SecretStore(folder/"vault")
if not key.exists():
    password=secrets.token_urlsafe(40)
    vault.set("signing_password",password)
    process=subprocess.run(["node",str(ROOT/"node_modules/@tauri-apps/cli/tauri.js"),"signer","generate",
                            "--ci","-w",str(key),"-p",password],capture_output=True,text=True,cwd=ROOT)
    if process.returncode:
        raise SystemExit("Signing key generation failed; no key material was printed.")
config_path=ROOT/"src-tauri/tauri.conf.json"
config=json.loads(config_path.read_text(encoding="utf-8"))
config["bundle"]["createUpdaterArtifacts"]=True
config["plugins"]={"updater":{"pubkey":key.with_suffix(".key.pub").read_text().strip(),
    "endpoints":["https://github.com/TUM17124/x-engagement-assistant/releases/latest/download/latest.json"],
    "requireSignedVersion":True,"windows":{"installMode":"passive"}}}
config_path.write_text(json.dumps(config,indent=2)+"\n",encoding="utf-8")
print("Release signing key stored encrypted outside the repository; public verification key configured.")
