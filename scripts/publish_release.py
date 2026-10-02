"""Maintainer opt-in: upload this tested installer as a GitHub release.
Uses Git's existing credential manager internally; never prints credentials.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import httpx

ROOT=Path(__file__).resolve().parent.parent
REPO="TUM17124/x-engagement-assistant"
parser=argparse.ArgumentParser()
parser.add_argument("--publish",action="store_true",help="Make the uploaded draft release public.")
args=parser.parse_args()
manifest=json.loads((ROOT/"artifacts/latest.json").read_text())
version=manifest["version"]
credential=subprocess.run(["git","credential","fill"],input="protocol=https\nhost=github.com\npath="+REPO+".git\n\n",
    text=True,capture_output=True,env={**os.environ,"GIT_TERMINAL_PROMPT":"0","GCM_INTERACTIVE":"Never"},cwd=ROOT)
if credential.returncode: raise SystemExit("GitHub credentials are unavailable. Sign in with Git Credential Manager.")
values=dict(line.split("=",1) for line in credential.stdout.splitlines() if "=" in line)
token=values.get("password")
if not token: raise SystemExit("GitHub credential manager did not supply authorization.")
headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json","User-Agent":"SocialCommand-release"}
commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
with httpx.Client(headers=headers,timeout=120) as client:
    base="https://api.github.com/repos/"+REPO
    response=client.get(base+"/releases")
    if response.status_code!=200: raise SystemExit("Could not list releases: HTTP "+str(response.status_code))
    existing=next((r for r in response.json() if r["tag_name"]=="v"+version),None)
    if existing and not existing["draft"]: raise SystemExit("This release is already public. Never replace signed public assets; publish a new version.")
    if existing:
        release=existing
    else:
        response=client.post(base+"/releases",json={"tag_name":"v"+version,"target_commitish":commit,
            "name":"Social Engagement Command Center "+version,"body":manifest["notes"],"draft":True,"prerelease":False})
        if response.status_code!=201: raise SystemExit("Could not create release: HTTP "+str(response.status_code))
        release=response.json()
    assets={a["name"]:a for a in release["assets"]}
    names=("Social-Engagement-Command-Center-Setup.exe","Social-Engagement-Command-Center-Setup.exe.sig","latest.json","SHA256.txt")
    for name in names:
        if name in assets:
            client.delete(base+"/releases/assets/"+str(assets[name]["id"])).raise_for_status()
        path=ROOT/"artifacts"/name
        url="https://uploads.github.com/repos/"+REPO+"/releases/"+str(release["id"])+"/assets"
        with path.open("rb") as content:
            response=client.post(url,params={"name":name},content=content,
                headers={"Content-Type":"application/octet-stream","Content-Length":str(path.stat().st_size)})
        if response.status_code!=201: raise SystemExit("Asset upload failed: "+name+" HTTP "+str(response.status_code)+". Release remains a draft.")
        print("Uploaded",name)
    if args.publish:
        response=client.patch(base+"/releases/"+str(release["id"]),json={"draft":False,"make_latest":"true"})
        if response.status_code!=200: raise SystemExit("Publishing failed; release remains a draft.")
        print("Published",response.json()["html_url"])
    else: print("Draft release ready for review:",release["html_url"])
