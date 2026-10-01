"""Local immutable originals, validated formats, and separate image derivatives."""
import io
import uuid
from pathlib import Path
from PIL import Image,ImageOps,UnidentifiedImageError
from . import database as db
Image.MAX_IMAGE_PIXELS=40_000_000
MIMES={"PNG":"image/png","JPEG":"image/jpeg","WEBP":"image/webp","GIF":"image/gif"}

def directory():
    p=db.DB_PATH.parent/"media";p.mkdir(parents=True,exist_ok=True);return p
def media_path(id):
    row=db.one("SELECT id FROM media WHERE id=?",(id,))
    if not row or not __import__("re").fullmatch("[a-f0-9]{32}",id):raise ValueError("Media not found.")
    p=directory()/id
    if not p.exists():raise ValueError("The media file is missing. Reimport the original.")
    return p

def add(data,name,parent_id=None):
    if not data or len(data)>50*1024*1024:raise ValueError("Choose a media file smaller than 50 MB.")
    width=height=None
    try:
        with Image.open(io.BytesIO(data)) as image:
            mime=MIMES.get(image.format)
            width,height=image.size
            if not mime:raise ValueError("Use PNG, JPG, WEBP, GIF, or MP4.")
            image.verify()
    except (UnidentifiedImageError,OSError):
        if len(data)>16 and data[4:8]==b"ftyp":mime="video/mp4"
        else:raise ValueError("This is not a supported image or MP4 file.") from None
    except (Image.DecompressionBombError,Image.DecompressionBombWarning):
        raise ValueError("Image dimensions are too large.") from None
    id=uuid.uuid4().hex
    directory().joinpath(id).write_bytes(data)
    db.execute("INSERT INTO media(id,name,mime,size,width,height,created_at,parent_id) VALUES(?,?,?,?,?,?,?,?)",
        (id,Path(name).name[:200],mime,len(data),width,height,db.now(),parent_id))
    return db.one("SELECT * FROM media WHERE id=?",(id,))

def transform(id,width,height,crop=None):
    if not 16<=width<=4096 or not 16<=height<=4096:raise ValueError("Choose dimensions from 16 to 4096 pixels.")
    with Image.open(media_path(id)) as source:
        image=ImageOps.exif_transpose(source).convert("RGB")
        if crop:
            if len(crop)!=4 or not (0<=crop[0]<crop[2]<=image.width and 0<=crop[1]<crop[3]<=image.height):raise ValueError("Crop bounds are outside this image.")
            image=image.crop(tuple(crop))
        image=ImageOps.fit(image,(width,height),method=Image.Resampling.LANCZOS)
        output=io.BytesIO();image.save(output,"PNG")
    return add(output.getvalue(),"edited-"+id[:8]+".png",id)
