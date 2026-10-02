"""Local mutations shared by terminal and GUI. Published safety history is retained."""
from . import database as db,workspace as ws,preferences as prefs

async def delete_draft(draft_id):
    async with ws.WRITE_LOCK:
        draft=ws.get_draft(draft_id)
        if draft["status"] in {"published","sending","uncertain","partial"}:
            raise ValueError("This draft was published, is being sent, or needs reconciliation. Use History and the original platform; local safety history cannot be erased to repost it.")
        with db.conn() as c:
            c.execute("DELETE FROM approved_content WHERE draft_id=?",(draft_id,))
            c.execute("UPDATE action_requests SET status='cancelled',finished_at=? WHERE status='pending' AND json_extract(arguments,'$.draft_id')=?",(db.now(),draft_id))
            c.execute("UPDATE scheduled_posts SET status='cancelled' WHERE draft_id=?",(draft_id,))
            # Keep the tombstone so SQLite cannot reuse a deleted ID for a later draft.
            c.execute("UPDATE drafts SET status='deleted',text='',generated_text='',updated_at=? WHERE id=?",(db.now(),draft_id))
        ws.activity("draft_deleted",draft,status="deleted")
        return {"deleted":True,"message":"Draft #"+str(draft_id)+" deleted from the inbox. Its schedule is cancelled. Activity and duplicate protection are preserved."}

def context_patch(section,fields):
    allowed={"voice":{"who","build","company","expertise","tone","never","like","hate"},
        "product":{"name","website","description","customers","features","problems","forbidden","cta"},
        "brand_voice":{"Tone","Humor level","Technical level","Preferred sentence length","Emoji preference","Words to avoid","Favorite phrases","Banned phrases"}}
    if set(fields)-allowed[section]:raise ValueError("Unknown context field. Read Settings for the supported field names.")
    values={**prefs.get(section),**fields};prefs.save({section:values})
    return {"message":"Writing context updated.","section":section,"fields":values}
