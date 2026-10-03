"""One catalog for adapters, setup links, and the UI. No credentials live here."""
import json
from pathlib import Path
from urllib.parse import urlsplit
import ipaddress
CATALOG = {row["id"]: row for row in json.loads(Path(__file__).with_name("ai_catalog.json").read_text(encoding="utf-8"))}

def is_loopback(url):
    host = urlsplit(url).hostname or ""
    if host == "localhost": return True
    try: return ipaddress.ip_address(host).is_loopback
    except ValueError: return False

def validate_url(value):
    u = urlsplit(value)
    if not u.hostname or u.username or u.password or u.query or u.fragment or "\\" in value:
        raise ValueError("Use an endpoint URL without credentials, query parameters or fragments.")
    if u.scheme != "https" and not (u.scheme == "http" and is_loopback(value)):
        raise ValueError("Use HTTPS, or HTTP for a local AI server.")
    try: u.port
    except ValueError: raise ValueError("Invalid endpoint port.") from None
    return value.rstrip("/")
