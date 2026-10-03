"""Compatibility entry point for the pasted-post workflow."""
from .providers import provider

async def draft_reply(tweet_text, author_username=""):
    return await provider("replies").generate_reply({"text":tweet_text,"username":author_username})
