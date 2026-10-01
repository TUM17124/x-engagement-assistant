from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from . import preferences as prefs
from .secrets import store, PUBLIC_SECRET_NAMES

router = APIRouter(prefix="/api")

def secret_name(name):
    return "ai_api_key_" + prefs.get("ai_provider") if name == "ai_api_key" else name

class SecretInput(BaseModel):
    value: str = Field(max_length=8192)

@router.get("/settings")
def read_settings():
    return {"settings": prefs.all_settings(), "secrets": {name: store.masked(secret_name(name)) for name in PUBLIC_SECRET_NAMES}}

@router.put("/settings")
def update_settings(values: dict):
    prefs.save(values)
    return read_settings()

@router.put("/secrets/{name}")
def replace_secret(name: str, value: SecretInput):
    if name not in PUBLIC_SECRET_NAMES:
        raise HTTPException(404, "Unknown credential.")
    store.set(secret_name(name), value.value.strip())
    if name == "ai_api_key":
        from .database import set_setting
        set_setting("ai_health",None)
    return {"masked": store.masked(secret_name(name))}

@router.delete("/secrets/{name}")
def delete_secret(name: str):
    if name not in PUBLIC_SECRET_NAMES:
        raise HTTPException(404, "Unknown credential.")
    store.delete(secret_name(name))
    return {"deleted": True}

@router.post("/secrets/{name}/reveal")
def reveal_secret(name: str):
    if name not in PUBLIC_SECRET_NAMES:
        raise HTTPException(404, "Unknown credential.")
    return {"value": store.get(secret_name(name)), "expires_in": 15}

@router.post("/onboarding/finish")
def finish():
    prefs.save({"onboarded": True})
    return {"ok": True}
