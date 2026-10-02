"""Grounded conversational summaries: no second model or invented action results."""
import json

YES={"yes","y","confirm","go ahead","yes please","yes post it","yes publish it","yes approve"}
NO={"no","n","cancel","cancel it","don't","do not","reject"}
def confirmation_word(text):
    value=text.strip().lower().rstrip('.!')
    return True if value in YES else False if value in NO else None

def describe(tool,value):
    if isinstance(value,dict):
        if value.get("published"):
            return "Published successfully. Confirmed post IDs: "+", ".join(value.get("post_ids",[]))+". You can open them from History."
        if tool=="accounts.list":pass
        if "connected" in value and "platform" in value:
            state=("Connected"+(" as "+value["name"] if value.get("name") else "")) if value["connected"] else "Not connected"
            return value["platform"].title()+": "+state+".\n"+value.get("message","")+"\n"+value.get("note","")+"\n"+"\n".join(str(i+1)+". "+step for i,step in enumerate(value.get("steps",[])))
        if tool=="system.status":
            cg=value["chatgpt"]
            return "Selected AI: "+value["selected_ai_provider"]+". ChatGPT: "+cg["state"]+"; plan usage "+("enabled" if cg["plan_usage"] else "not enabled")+".\n"+describe("accounts.list",value["social_accounts"])+"\nScheduler: "+value["scheduler"]+". Drafts waiting: "+str(value["waiting_drafts"])+". Active automations: "+str(value["active_automations"])+"."
        if value.get("skipped"):return "I skipped this item because it did not produce a useful response. Nothing was posted."
        draft=value.get("draft",value)
        if isinstance(draft,dict) and "id" in draft and "text" in draft and "kind" in draft:
            return "Draft #"+str(draft["id"])+" on "+draft.get("platform","x")+" ("+draft["status"]+"):\n\n"+draft["text"]+"\n\nYou can ask me to edit it, type 'publish "+str(draft["id"])+"' to review a posting request, or 'manual "+str(draft["id"])+"' to open the platform composer."
        if "text" in value:return value["text"]+("\n\nSaved in AI Planner. Nothing has been scheduled." if tool=="content.weeklyPlan" else "")
        if "scans" in value:return "\n".join(x["platform"]+": "+(x.get("message") or str(x["count"])+" posts imported.") for x in value["scans"])
        if value.get("message"):return value["message"]
        if value.get("scheduled"):return "The exact approved content has been scheduled. Keep the app running. See Schedule for its status."
        if value.get("ok"):return "Connection test passed."
        if value.get("saved"):return "Saved. You can view it in the matching app screen."
        if value.get("removed") or value.get("deleted"):return "Removed from the local workspace."
        if tool=="approvals.list":return str(len(value["drafts"]))+" drafts need review; "+str(len(value["actions"]))+" action requests are pending. Open Approval Center to see all, or name a draft."
    if isinstance(value,list):
        if not value:return "There are no items here yet. Import a post, create a draft, or connect an account to get started."
        if tool=="accounts.list":return "\n".join(v["platform"].title()+": "+("Connected" if v["connected"] else "Not connected")+(" ? "+v["name"] if v.get("name") else "") for v in value)+"\nAsk 'is Facebook connected?' or 'connect Facebook' for guidance."
        if tool=="drafts.list":return "\n\n".join(describe("draft",v) for v in value[:10])
        return str(len(value))+" items found. Open the details below or the matching screen."
    return "Action completed. See details below."
