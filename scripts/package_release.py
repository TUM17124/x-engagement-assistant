"""Create and verify release assets from a signed Windows build."""
import base64
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
import shutil
ROOT=Path(__file__).resolve().parent.parent
config=json.loads((ROOT/"src-tauri/tauri.conf.json").read_text(encoding="utf-8"))
version=config["version"]
source=ROOT/"src-tauri/target/release/bundle/nsis"/f"Social Engagement Command Center_{version}_x64-setup.exe"
signature=source.with_suffix(".exe.sig")
data=source.read_bytes()
public_lines=base64.b64decode(config["plugins"]["updater"]["pubkey"]).decode().splitlines()
public=base64.b64decode(public_lines[1])
lines=base64.b64decode(signature.read_text().strip()).decode().splitlines()
signed=base64.b64decode(lines[1])
if signed[:2]!=b"ED" or public[2:10]!=signed[2:10]:
    raise SystemExit("Unexpected release signature format or signing key.")
key=Ed25519PublicKey.from_public_bytes(public[10:])
key.verify(signed[10:],hashlib.blake2b(data,digest_size=64).digest())
comment=lines[2].removeprefix("trusted comment: ")
key.verify(base64.b64decode(lines[3]),signed[10:]+comment.encode())
if "version:"+version not in comment and "version: "+version not in comment:
    raise SystemExit("The signature does not bind the expected version.")
out=ROOT/"artifacts";out.mkdir(exist_ok=True)
name="Social-Engagement-Command-Center-Setup.exe"
shutil.copy2(source,out/name)
shutil.copy2(signature,out/(name+".sig"))
(out/"SHA256.txt").write_text(hashlib.sha256(data).hexdigest()+"  "+name+"\n")
notes=(ROOT/"docs/RELEASE-NOTES.md").read_text(encoding="utf-8")
manifest={"version":version,"notes":notes,"pub_date":datetime.now(timezone.utc).isoformat(),
          "platforms":{"windows-x86_64":{"signature":signature.read_text().strip(),
          "url":f"https://github.com/TUM17124/x-engagement-assistant/releases/download/v{version}/{name}"}}}
(out/"latest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
print("Verified signed installer, version binding, update manifest and SHA-256:",version)
