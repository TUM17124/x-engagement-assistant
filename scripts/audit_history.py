"""Scan all reachable Git blobs for credential patterns and local configured secrets."""
import subprocess
from secret_scan import check
from dotenv import dotenv_values
values=[v.encode() for k,v in dotenv_values(".env").items() if v and len(v)>12 and any(x in k for x in ("KEY","TOKEN","SECRET"))]
objects=subprocess.check_output(["git","rev-list","--objects","--all"],text=True).splitlines()
issues=[]
count=0
for line in objects:
    fields=line.split(" ",1)
    if len(fields)!=2:
        continue
    oid,name=fields
    kind=subprocess.check_output(["git","cat-file","-t",oid],text=True).strip()
    if kind!="blob":
        continue
    content=subprocess.check_output(["git","cat-file","blob",oid])
    issue=check(name,content)
    if any(value in content for value in values):
        issue="configured credential"
    if issue:
        issues.append(name+": "+issue)
    count+=1
if issues:
    print("\n".join(sorted(set(issues))))
    print("Rotate any exposed credential; deleting it from the latest tree is not sufficient.")
    raise SystemExit(1)
print(f"Git history audit passed: {count} reachable blobs; no recognized secrets or configured credential values found.")
