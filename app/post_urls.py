import re
from urllib.parse import urlsplit


def parse_tweet_url(value: str) -> dict[str, str]:
    """Parse locally; never fetch the post or resolve redirects."""
    error = "Enter a valid X post URL, such as https://x.com/username/status/123456789."
    value = value.strip()
    try:
        url = urlsplit(value)
        if (url.scheme not in {"https", "http"}
                or url.netloc.lower() not in {
                    "x.com", "www.x.com", "mobile.x.com",
                    "twitter.com", "www.twitter.com", "mobile.twitter.com",
                }
                or any(c.isspace() for c in value)):
            raise ValueError(error)
        match = re.fullmatch(
            r"/([A-Za-z0-9_]{1,15})/status/([1-9][0-9]{0,19})/?", url.path
        )
        if not match:
            raise ValueError(error)
    except ValueError:
        raise ValueError(error) from None
    username, tweet_id = match.groups()
    return {
        "author_username": username,
        "tweet_id": tweet_id,
        "tweet_url": f"https://x.com/{username}/status/{tweet_id}",
    }
