"""Separate image generation and vision assistance, invoked only by explicit UI actions."""
from abc import ABC,abstractmethod
import base64
import io
from urllib.parse import urlsplit,quote
import httpx
from PIL import Image,ImageOps
from . import preferences as prefs,media
from .secrets import store
from .errors import request

class ImageProvider(ABC):
    @abstractmethod
    async def generate(self,prompt):...

class CompatibleImageProvider(ImageProvider):
    async def generate(self,prompt):
        cfg=prefs.get("image_provider")
        endpoint=cfg.get("endpoint","").rstrip("/")
        url=urlsplit(endpoint)
        if (url.scheme!="https" and not(url.scheme=="http" and url.hostname in {"localhost","127.0.0.1"})) or url.username or url.password or url.query:
            raise ValueError("Configure an HTTPS image endpoint, or a local HTTP endpoint, in AI Provider.")
        from .ai_connections import policy
        from .ai_registry import is_loopback
        if policy().local_only and not is_loopback(endpoint):raise ValueError("Local AI Only blocks cloud image generation.")
        key=store.get("image_api_key")
        async with httpx.AsyncClient(timeout=120) as client:
            r=await request(client,"POST",endpoint+"/images/generations","Image AI",headers={"Authorization":"Bearer "+key},
                json={"model":cfg.get("model",""),"prompt":prompt,"n":1,"size":"1024x1024","response_format":"b64_json"})
        try:
            data=base64.b64decode(r.json()["data"][0]["b64_json"],validate=True)
        except (KeyError,IndexError,ValueError,TypeError):
            raise ValueError("This adapter requires a base64 image response. Remote download URLs are not fetched.") from None
        return media.add(data,"generated.png")

async def describe(id,instruction):
    from .providers import provider
    selected=provider("vision")
    if not hasattr(selected,"vision"):raise ValueError("The selected adapter currently supports text. Choose a vision provider in AI Providers > Advanced feature selection.")
    row=__import__("app.database",fromlist=["one"]).one("SELECT * FROM media WHERE id=?",(id,))
    if not row or not row["mime"].startswith("image/"):raise ValueError("Choose an image for visual assistance.")
    with Image.open(media.media_path(id)) as source:
        image=ImageOps.exif_transpose(source).convert("RGB");image.thumbnail((1024,1024))
        out=io.BytesIO();image.save(out,"JPEG",quality=85)
    encoded=base64.b64encode(out.getvalue()).decode()
    return await selected.vision(instruction[:1000],encoded)
