import json
from fastapi import APIRouter,UploadFile,File
from fastapi.responses import FileResponse
from . import database as db,media,workspace as ws

router=APIRouter(prefix="/api/media")

@router.get("")
def library(q:str="",folder:str="",favorite:bool=False):
    sql="SELECT * FROM media WHERE 1=1";args=[]
    if q:sql+=" AND (name LIKE ? OR tags LIKE ? OR caption LIKE ?)";args+=["%"+q+"%"]*3
    if folder:sql+=" AND folder=?";args.append(folder)
    if favorite:sql+=" AND favorite=1"
    return db.rows(sql+" ORDER BY created_at DESC",args)

@router.post("")
async def upload(file:UploadFile=File(...)):
    return media.add(await file.read(50*1024*1024+1),file.filename or "upload")

@router.get("/{id}/file")
def file(id:str,download:bool=False):
    row=db.one("SELECT * FROM media WHERE id=?",(id,))
    if not row:raise ValueError("Media not found.")
    return FileResponse(media.media_path(id),media_type=row["mime"],filename=row["name"] if download else None)

@router.put("/{id}")
def update(id:str,data:dict):
    allowed={"tags","folder","favorite","caption","alt_text"}
    if set(data)-allowed:raise ValueError("Unknown media field.")
    if not db.one("SELECT id FROM media WHERE id=?",(id,)):raise ValueError("Media not found.")
    for key,value in data.items():
        if key=="favorite":value=int(bool(value))
        elif not isinstance(value,str) or len(value)>4000:raise ValueError("Media metadata must be short text.")
        db.execute("UPDATE media SET "+key+"=? WHERE id=?",(value,id))
    return {"saved":True}

@router.post("/{id}/transform")
def transform(id:str,data:dict):
    try:return media.transform(id,int(data["width"]),int(data["height"]),data.get("crop"))
    except (KeyError,TypeError):raise ValueError("Specify width and height, and optional crop bounds.") from None

@router.get("/{id}/usage")
def usage(id:str):return db.rows("SELECT u.*,d.platform,d.status,d.text FROM media_usage u JOIN drafts d ON d.id=u.draft_id WHERE media_id=?",(id,))

@router.delete("/{id}")
def delete(id:str):
    if any(id in json.loads(r["media_ids"]) for r in db.rows("SELECT media_ids FROM drafts WHERE status NOT IN ('published','skipped')")):
        raise ValueError("Remove this media from active drafts before deleting it.")
    media.media_path(id).unlink()
    db.execute("DELETE FROM media WHERE id=?",(id,))
    return {"deleted":True}

@router.post("/{id}/assist")
async def assist(id:str,data:dict):
    from .image_providers import describe
    return {"text":await ws.ai_call(lambda:describe(id,str(data.get("instruction","Suggest accurate alt text and three useful caption ideas."))))}

@router.post("/generate/image")
async def generate(data:dict):
    from .image_providers import CompatibleImageProvider
    prompt=str(data.get("prompt","")).strip()
    if not prompt or len(prompt)>4000:raise ValueError("Enter an image prompt up to 4000 characters.")
    return await ws.ai_call(lambda:CompatibleImageProvider().generate(prompt))
