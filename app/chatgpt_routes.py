from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from .chatgpt_auth import auth
from .chatgpt_provider import ChatGPTPlanProvider
from . import preferences as prefs

router=APIRouter(prefix="/api/chatgpt")

class Connect(BaseModel):
    model_config=ConfigDict(extra="forbid")
    profile_id:str|None=None
    new_profile:bool=False
    enable_plan:bool=False

@router.get("/status")
def status():return auth.get_connection_status()

@router.post("/connect")
async def connect(data:Connect):
    return await auth.connect(data.profile_id,data.new_profile,data.enable_plan)

@router.post("/select/{profile_id}")
async def select(profile_id:str):
    return await auth.select(profile_id)

@router.post("/disconnect")
async def disconnect():
    from .terminal_routes import cancel_all
    await cancel_all()
    return await auth.disconnect()

@router.post("/retry")
def retry():return auth.retry()

@router.post("/models")
async def models():return await ChatGPTPlanProvider().get_models()

@router.post("/cancel-login")
async def cancel_login():
    await auth.close_listener()
    return auth.get_connection_status()
