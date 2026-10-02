"""Pre-commit/CI secret checks; prints filenames and categories, never credential values."""
import re
import subprocess
import sys
from pathlib import Path

PATTERNS=[
    (re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),"private key"),
    (re.compile(rb"AIza[0-9A-Za-z_-]{30,}"),"Google API key"),
    (re.compile(rb"(?:ghp_|github_pat_)[A-Za-z0-9_]{30,}"),"GitHub token"),
    (re.compile(rb"sk-(?:proj-)?[A-Za-z0-9_-]{30,}"),"AI API key"),
]
def check(name,content):
    if Path(name).name in {"chatgpt-host.json","chatgpt-auth.json"}:
        return "private ChatGPT installation/credential file"
    if name!=".env.example" and (Path(name).name.startswith(".env") or re.search(r"\.(db|sqlite3?|pem|key|bin)(-|$)",name)):
        return "private credential/data file"
    for pattern,label in PATTERNS:
        if pattern.search(content):
            return label
    return None

def main():
    staged="--staged" in sys.argv
    names=subprocess.check_output(["git","diff","--cached","--name-only","--diff-filter=ACM"] if staged else ["git","ls-files"],text=True).splitlines()
    errors=[]
    for name in names:
        if not Path(name).is_file() and not staged:
            continue
        data=subprocess.check_output(["git","show",":"+name]) if staged else Path(name).read_bytes()
        issue=check(name,data)
        if issue:
            errors.append(f"{name}: {issue}")
    # Compare developer-configured credential values without printing them.
    try:
        from dotenv import dotenv_values
        values=[v.encode() for k,v in dotenv_values(".env").items() if v and len(v)>12 and any(w in k for w in ("KEY","TOKEN","SECRET"))]
        for name in names:
            if Path(name).is_file():
                data=subprocess.check_output(["git","show",":"+name]) if staged else Path(name).read_bytes()
                if any(v in data for v in values):
                    errors.append(name+": configured credential detected")
    except ImportError:
        pass
    if errors:
        print("\n".join(errors));raise SystemExit(1)
    print(f"Secret audit passed: {len(names)} files.")
if __name__=="__main__":
    main()
