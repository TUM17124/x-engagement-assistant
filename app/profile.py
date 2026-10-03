"""Structured local user profile, shared by Settings, AI context and terminal tools."""
from typing import Any
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from . import preferences as prefs
from .validation import log_validation, safe_errors

router=APIRouter(prefix="/api/profile")

class ProfilePatch(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    name:str=Field(default="",max_length=160)
    role:str=Field(default="",max_length=240)
    bio:str=Field(default="",max_length=4000)
    industry:str=Field(default="",max_length=240)
    expertise:str=Field(default="",max_length=4000)
    products:str=Field(default="",max_length=4000)
    audience:str=Field(default="",max_length=4000)
    goals:str=Field(default="",max_length=4000)

    @field_validator("*",mode="before")
    @classmethod
    def optional_text(cls,value):
        if value is None:return ""
        return value.strip() if isinstance(value,str) else value

def get_profile():
    old=prefs.get("my_profile") or {}
    # Read earlier Title Case fields without destroying existing local configuration.
    return {name:old.get(name,old.get(name.title(),"")) for name in ProfilePatch.model_fields}

def save_profile(patch:ProfilePatch):
    value={**get_profile(),**patch.model_dump(exclude_unset=True)}
    prefs.save({"my_profile":value})
    actual=get_profile()
    if actual!=value:raise ValueError("Profile save could not be verified. Reopen Settings before retrying.")
    return actual

@router.get("")
def read_profile():return get_profile()

@router.put("")
def update_profile(payload:Any=Body(...)):
    try: patch=ProfilePatch.model_validate(payload)
    except ValidationError as error:
        log_validation("profile",error,ProfilePatch.model_fields)
        raise HTTPException(422,detail=safe_errors(error,ProfilePatch.model_fields)) from None
    return save_profile(patch)
