"""Compatibility facade for existing OAuth and publishing code."""
import secrets
from . import preferences
from .secrets import store

class Settings:
    def __getattr__(self, key):
        if key in {"x_client_secret", "x_bearer_token", "ai_api_key"}:
            return store.get("ai_api_key_" + preferences.get("ai_provider") if key == "ai_api_key" else key)
        if key == "session_secret":
            value = store.get("session_secret")
            if not value:
                value = secrets.token_urlsafe(48)
                store.set("session_secret", value)
            return value
        if key in preferences.DEFAULTS:
            return preferences.get(key)
        raise AttributeError(key)

settings = Settings()
