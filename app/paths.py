"""Paths shared by source and bundled builds. Never write into the install directory."""
import os
import sys
from pathlib import Path

VERSION = "0.2.0"
def data_dir():
    override = os.getenv("XEA_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "XEngagementAssistant"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/XEngagementAssistant"
    return Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local/share")) / "XEngagementAssistant"

def resources():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "app"
