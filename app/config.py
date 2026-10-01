from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    x_client_id: str = os.getenv("X_CLIENT_ID", "")
    x_client_secret: str = os.getenv("X_CLIENT_SECRET", "")
    x_redirect_uri: str = os.getenv("X_REDIRECT_URI", "http://127.0.0.1:8787/auth/callback")
    session_secret: str = os.getenv("SESSION_SECRET", "dev-only-change-me")
    default_query: str = os.getenv(
        "DEFAULT_QUERY",
        '("pdf editor" OR ebooks OR "indie hacker" OR SaaS OR authors OR "reading app") lang:en -is:retweet'
    )

    ai_base_url: str = os.getenv("AI_BASE_URL", "").rstrip("/")
    ai_api_key: str = os.getenv("AI_API_KEY", "")
    ai_model: str = os.getenv("AI_MODEL", "")

    daily_write_cap: int = 100

settings = Settings()
