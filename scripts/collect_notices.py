"""Collect resolved dependency license metadata and upstream notices for releases."""
import importlib.metadata as metadata
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent

def notice_file(path):
    name = path.name.lower()
    return path.is_file() and any(name.startswith(word) for word in ("license", "licence", "copying", "notice", "copyright"))

def main():
    entries = []
    notices = ["X Engagement Assistant: third-party notices\nOriginal application code is MIT; each dependency retains its license.\n"]
    for dist in sorted(metadata.distributions(), key=lambda d: d.metadata["Name"].lower()):
        name, version = dist.metadata["Name"], dist.version
        license_name = dist.metadata.get("License-Expression") or dist.metadata.get("License") or "See upstream notices"
        entries.append({"ecosystem":"Python", "name":name, "version":version, "license":license_name})
        notices.append(f"\n=== Python: {name} {version} ===\n{license_name}\n")
        for item in dist.files or []:
            if notice_file(Path(dist.locate_file(item))):
                notices.append(Path(dist.locate_file(item)).read_text(encoding="utf-8",errors="replace"))
    result = subprocess.run(["cargo","metadata","--manifest-path",str(ROOT/"src-tauri/Cargo.toml"),
        "--format-version","1","--locked","--offline"],check=True,capture_output=True,text=True,encoding="utf-8")
    for package in sorted(json.loads(result.stdout)["packages"], key=lambda p:p["name"]):
        if not package["source"]:
            continue
        entries.append({"ecosystem":"Rust", "name":package["name"], "version":package["version"], "license":package["license"] or "See upstream notices"})
        notices.append(f'\n=== Rust: {package["name"]} {package["version"]} ===\n{package["license"] or ""}\n')
        folder=Path(package["manifest_path"]).parent
        paths={p for p in folder.iterdir() if notice_file(p)}
        if package.get("license_file"):
            paths.add(folder/package["license_file"])
        for sub in ("licenses","LICENSES"):
            if (folder/sub).is_dir():
                paths.update(p for p in (folder/sub).rglob("*") if p.is_file())
        for path in sorted(paths):
            if path.is_file():
                notices.append(path.read_text(encoding="utf-8",errors="replace"))
    (ROOT/"docs/DEPENDENCIES.json").write_text(json.dumps(entries,indent=2)+"\n",encoding="utf-8")
    (ROOT/"docs/THIRD_PARTY_NOTICES.txt").write_text("\n".join(notices),encoding="utf-8")
    print(f"Collected license metadata and notices for {len(entries)} resolved packages.")

if __name__=="__main__":
    main()

