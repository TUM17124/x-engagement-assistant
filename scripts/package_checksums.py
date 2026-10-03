"""Hash native installer artifacts without publishing them."""
import hashlib, os, shutil, platform
from pathlib import Path
root=Path(__file__).resolve().parent.parent
files=sorted(p for p in (root/"src-tauri/target/release/bundle").rglob("*") if p.suffix in {".dmg",".deb",".AppImage",".exe"})
if not files:raise SystemExit("No native installers were produced.")
out=root/"artifacts";out.mkdir(exist_ok=True)
arch="arm64" if platform.machine().lower() in {"arm64","aarch64"} else "x64"
lines=[]
for path in files:
    with path.open("rb") as f:digest=hashlib.file_digest(f,"sha256").hexdigest()
    name="Social-Engagement-Command-Center-"+arch+path.suffix
    shutil.copy2(path,out/name)
    lines.append(digest+"  "+name)
out=root/"artifacts";out.mkdir(exist_ok=True)
(out/("SHA256-"+os.environ.get("TAURI_ENV_TARGET_TRIPLE","native")+".txt")).write_text("\n".join(lines)+"\n")
