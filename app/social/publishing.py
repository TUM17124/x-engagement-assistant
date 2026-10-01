"""Only invoked after the domain has verified approval and claimed a send."""
import json
from .registry import provider
from .. import database as db
from ..media import media_path

async def send_approved(draft,text):
    p=provider(draft["platform"])
    if not draft["account_id"] or p.account.get("account_id")!=draft["account_id"]:
        raise ValueError("The connected account changed. Review and approve this draft again.")
    caps=p.capabilities()
    media=[db.one("SELECT * FROM media WHERE id=?",(id,)) for id in json.loads(draft["media_ids"])]
    for item in media:
        if not item:raise ValueError("Attached media is missing. Edit and approve again.")
        media_path(item["id"])
        if item["mime"]=="video/mp4" or not caps["can_upload_images"]:
            raise ValueError("This platform uses manual handoff for the selected media.")
    if draft["kind"]=="original":
        if not caps["can_publish"]:p.unsupported("API publishing")
        return await p.publish_post(text,media)
    source=db.one("SELECT * FROM feed_items WHERE id=?",(draft["feed_id"],))
    if not source or not source["external_id"] or not source["source"].startswith("API"):
        raise ValueError("This manually imported response uses copy-and-open. Import the target through an authorized API to attempt an API response.")
    if draft["kind"]=="reply" and caps["can_reply"]:
        return await p.publish_reply(source["external_id"],text)
    if draft["kind"]=="comment" and caps["can_comment"]:
        return await p.publish_comment(source["external_id"],text)
    p.unsupported("this response action")
