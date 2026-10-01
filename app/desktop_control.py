"""Only the owning desktop process knows this ephemeral control token."""
import os
import secrets
from fastapi import APIRouter,Request,HTTPException
from . import preferences as prefs,database as db
router=APIRouter(prefix="/desktop")
shutdown_handler=None

def authorize(request):
    token=os.getenv("XEA_DESKTOP_TOKEN","")
    if not token or not secrets.compare_digest(token,request.headers.get("X-Desktop-Token","")):
        raise HTTPException(403,"Desktop control is private.")

@router.get("/state")
def state(request:Request):
    authorize(request)
    return {"tray_enabled":prefs.get("tray_enabled"),"monitoring":prefs.get("monitoring") or prefs.get("assistant_mode"),
            "notifications":prefs.get("notifications")}

@router.get("/events")
def events(request:Request):
    authorize(request)
    if not prefs.get("notifications"):
        return []
    with db.conn() as c:
        rows=c.execute("SELECT * FROM notifications WHERE delivered=0 ORDER BY id LIMIT 5").fetchall()
        for row in rows:
            c.execute("UPDATE notifications SET delivered=1 WHERE id=?",(row["id"],))
    return [dict(row) for row in rows]

@router.post("/monitoring/{enabled}")
def monitoring(request:Request,enabled:bool):
    authorize(request)
    prefs.save({"monitoring":enabled,"assistant_mode":enabled})
    return {"ok":True}

@router.post("/shutdown")
def shutdown(request:Request):
    authorize(request)
    if shutdown_handler:
        shutdown_handler()
    return {"ok":True}
