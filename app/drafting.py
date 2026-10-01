import httpx
from .config import settings

SYSTEM = '''You write concise, natural X replies for a software founder.
Never sound spammy. Never pretend to have used something you have not used.
Do not force a product mention. Add value to the conversation first.
Maximum 240 characters. No hashtags unless genuinely useful.'''

async def draft_reply(tweet_text: str, author_username: str = "") -> str:
    if not settings.ai_base_url or not settings.ai_model:
        raise RuntimeError("Configure AI_BASE_URL and AI_MODEL in .env before generating a reply.")
    headers = {"Content-Type": "application/json"}
    if settings.ai_api_key:
        headers["Authorization"] = f"Bearer {settings.ai_api_key}"
    body = {
        "model": settings.ai_model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": f"Write one reply to @{author_username}:\n\n{tweet_text}",
            },
        ],
        "temperature": 0.8,
        "max_tokens": 512,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{settings.ai_base_url}/chat/completions",
            headers=headers,
            json=body,
        )
        r.raise_for_status()
        try:
            text = r.json()["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError, AttributeError, ValueError):
            raise RuntimeError("The AI returned no usable reply. Please regenerate.") from None
        if not text:
            raise RuntimeError("The AI returned an empty reply. Please regenerate.")
        return text[:280]
