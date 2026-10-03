"""Canonical Settings schemas shared by GUI saves and AI action previews."""
import json
from pydantic import BaseModel, ConfigDict, Field, model_validator
from . import database as db
from .profile import ProfilePatch, get_profile

FIELDS = {
    "voice": ["who", "build", "company", "expertise", "tone", "never", "like", "hate"],
    "product": ["name", "website", "description", "customers", "features", "problems", "forbidden", "cta"],
    "brand_voice": ["Tone", "Humor level", "Technical level", "Preferred sentence length", "Emoji preference", "Words to avoid", "Favorite phrases", "Banned phrases"],
    "my_profile": list(ProfilePatch.model_fields),
}
LABELS = {"my_profile":"My Profile", "voice":"Writing Voice", "brand_voice":"Brand Voice", "product":"My Product"}

def canonical_fields(section, fields):
    if section not in FIELDS or not isinstance(fields, dict):
        raise ValueError("Choose a valid profile section and named text fields.")
    names = {k.lower().replace(" ", "_"): k for k in FIELDS[section]}
    result = {}
    for key, value in fields.items():
        canonical = names.get(key.lower().replace(" ", "_")) if isinstance(key,str) else None
        if canonical is None:
            raise ValueError("Unknown field for " + LABELS[section] + ". Allowed fields: " + ", ".join(FIELDS[section]))
        if canonical in result:
            raise ValueError("The same field was supplied more than once.")
        if value is None: value = ""
        if not isinstance(value,str) or len(value)>4000:
            raise ValueError("Each profile field must be text of at most 4000 characters.")
        result[canonical] = value.strip()
    if section == "my_profile":
        result = ProfilePatch.model_validate(result).model_dump(exclude_unset=True)
    return result

def current_context():
    return {section: get_profile() if section=="my_profile" else db.get_setting(section,{}) for section in FIELDS}

class ContextUpdate(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    my_profile: ProfilePatch | None = None
    brand_voice: dict[str,str] | None = Field(default=None,description="Exact keys: " + ", ".join(FIELDS["brand_voice"]))
    voice: dict[str,str] | None = Field(default=None,description="Exact keys: " + ", ".join(FIELDS["voice"]))
    product: dict[str,str] | None = Field(default=None,description="Exact keys: " + ", ".join(FIELDS["product"]))

    @model_validator(mode="after")
    def validate_sections(self):
        count=0
        for section, fields in self.model_dump(exclude_unset=True,exclude_none=True).items():
            canonical=canonical_fields(section,fields)
            if section != "my_profile":setattr(self,section,canonical)
            count+=len(canonical)
        if not count:raise ValueError("Supply at least one named profile field to update.")
        return self

def save_context(patch):
    from . import preferences as prefs
    changes=patch.model_dump(exclude_unset=True,exclude_none=True)
    before=current_context()
    merged={section:{**before[section],**fields} for section,fields in changes.items()}
    prefs.save(merged)
    actual=current_context()
    if any(actual[section]!=value for section,value in merged.items()):
        raise ValueError("The saved profile could not be verified. Reopen Settings before retrying.")
    return {"verified":True,"settings":{k:actual[k] for k in merged},
            "saved_fields":{k:list(v) for k,v in changes.items()},
            "message":"Saved and verified: " + "; ".join(LABELS[k]+" ("+", ".join(v)+")" for k,v in changes.items()) + ". Other settings were not changed."}
