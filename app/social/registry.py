from .x import XProvider
from .facebook import FacebookProvider
from .instagram import InstagramProvider
from .linkedin import LinkedInProvider
from .tiktok import TikTokProvider
from .youtube import YouTubeProvider
from .threads import ThreadsProvider

PROVIDERS={p.platform:p for p in (XProvider,FacebookProvider,InstagramProvider,LinkedInProvider,TikTokProvider,YouTubeProvider,ThreadsProvider)}

def provider(platform):
    if platform not in PROVIDERS:raise ValueError("Unknown social provider.")
    return PROVIDERS[platform]()
