"""Local terminal streaming endpoints; confirmation is never an agent tool."""
import asyncio
import json
import uuid
from zoneinfo import ZoneInfo
from fastapi import APIRouter,Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel,Field,ConfigDict
from . import database as db
from . import command_bus as bus
from .command_tools import catalog
from .chatgpt_provider import STREAM_SINK

router=APIRouter(prefix="/api/terminal")
TASKS={}
QUEUES={}

class Command(BaseModel):
    model_config=ConfigDict(extra="forbid")
    id:str=Field(default_factory=lambda:str(uuid.uuid4()))
    text:str=Field(min_length=1,max_length=64000)
    timezone:str="UTC"
    approval_id:str|None=None
    approval_checksum:str|None=Field(default=None,min_length=64,max_length=64)

@router.get("/context")
def terminal_context():
    from .terminal_context import hints
    return hints()

@router.get("/tools")
def tools():return catalog()

@router.get("/history")
def history(search:str=""):
    return db.rows("SELECT * FROM terminal_commands WHERE raw_input LIKE ? ORDER BY created_at DESC LIMIT 100",("%"+search[:200]+"%",))

@router.get("/approvals")
def approvals():return db.rows("SELECT * FROM action_requests WHERE status='pending' ORDER BY created_at DESC LIMIT 100")

@router.get("/automations")
def automations():
    return {"items":db.rows("SELECT * FROM automations WHERE status<>'deleted' ORDER BY id DESC"),
            "runs":db.rows("SELECT * FROM automation_runs ORDER BY id DESC LIMIT 100"),
            "paused":db.get_setting("automations_paused",False)}

@router.get("/memory")
def memory():return db.rows("SELECT * FROM application_memory ORDER BY key")

async def run_command(data,queue):
    completed=[]
    def emit(value):
        if value.get("type")=="tool_result":completed.append({"tool":value["tool"],"result":bus.redact(value["data"])})
        if queue.qsize()<2000:queue.put_nowait(bus.redact(value))
    marker=STREAM_SINK.set(emit)
    try:
        async with bus.BUS_LOCK:
            decision=bus.confirmation_word(data.text)
            if decision is not None:
                result=await bus.terminal_confirmation(decision,data.approval_id,data.approval_checksum,data.id,emit)
            else:
                plan=await bus.parse(data.text,data.timezone,emit)
                validated=bus.validate(plan)
                risks=[s.permission.value for s,a in validated]
                risk="DESTRUCTIVE" if "DESTRUCTIVE" in risks else "EXTERNAL_ACTION" if "EXTERNAL_ACTION" in risks else "DRAFT" if "DRAFT" in risks else "READ_ONLY"
                db.execute("UPDATE terminal_commands SET parsed_intent=?,arguments=?,risk_level=?,requires_approval=? WHERE id=?",
                    (",".join(a.tool for a in plan.actions),json.dumps(bus.redact([a.model_dump() for a in plan.actions])),risk,
                     risk in {"EXTERNAL_ACTION","DESTRUCTIVE"},data.id))
                result=await bus.execute_plan(plan,data.id,emit)
            from .terminal_feedback import completion_report
            result["report"]=completion_report(result)
            if not result.get("approvalIds") and not result.get("choices"):
                from .terminal_context import followups
                result["question"],result["choices"]=followups(result)
            db.execute("UPDATE terminal_commands SET status='completed',finished_at=?,result=? WHERE id=?",(db.now(),json.dumps(bus.redact(result)),data.id))
            emit({"type":"result",**result})
    except asyncio.CancelledError:
        db.execute("UPDATE terminal_commands SET status='cancelled',finished_at=? WHERE id=?",(db.now(),data.id))
        emit({"type":"cancelled","text":"Command stopped. Completed local work is retained; inspect history before retrying."})
    except Exception as error:
        from .errors import ServiceError
        message=str(error) if isinstance(error,(ValueError,ServiceError)) else "The command failed. Check connection status; completed local work is retained."
        if completed:message+=" Completed before this failure: "+", ".join(v["tool"] for v in completed)+". Those changes are retained."
        message=bus.redact(message)
        db.execute("UPDATE terminal_commands SET status='failed',finished_at=?,result=? WHERE id=?",(db.now(),json.dumps({"error":message,"data":completed,"report":{"state":"attention","message":message}}),data.id))
        emit({"type":"error","text":message,"technical":error.details()["technical"] if isinstance(error,ServiceError) else ""})
    finally:
        STREAM_SINK.reset(marker)
        emit({"type":"done"})
        TASKS.pop(data.id,None)

@router.post("/run")
async def run(data:Command,request:Request):
    data.text=bus.safe_input(data.text)
    try:uuid.UUID(data.id);ZoneInfo(data.timezone)
    except (ValueError,KeyError):raise ValueError("Use a valid request ID and timezone.") from None
    existing=db.one("SELECT * FROM terminal_commands WHERE id=?",(data.id,))
    if existing:raise ValueError("This command ID was already used. Inspect history; it will not be replayed.")
    if TASKS:raise ValueError("A terminal command is running. Stop it or wait for completion.")
    db.execute("INSERT INTO terminal_commands(id,source,raw_input,status,created_at) VALUES(?,'terminal',?,'running',?)",(data.id,data.text,db.now()))
    queue=asyncio.Queue()
    task=asyncio.create_task(run_command(data,queue));TASKS[data.id]=task
    async def events():
        try:
            yield "data: "+json.dumps({"type":"started","id":data.id})+"\n\n"
            while True:
                try:event=await asyncio.wait_for(queue.get(),15)
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n";continue
                yield "data: "+json.dumps(event)+"\n\n"
                if event["type"]=="done":break
        finally:
            if not task.done():task.cancel()
            await asyncio.gather(task,return_exceptions=True)
    return StreamingResponse(events(),media_type="text/event-stream",headers={"X-Accel-Buffering":"no"})

@router.post("/cancel/{id}")
async def cancel(id:str):
    task=TASKS.get(id)
    if task:task.cancel();await asyncio.gather(task,return_exceptions=True)
    return {"cancelled":bool(task)}

async def cancel_all():
    tasks=list(TASKS.values())
    for task in tasks:task.cancel()
    await asyncio.gather(*tasks,return_exceptions=True)

class Confirmation(BaseModel):
    model_config=ConfigDict(extra="forbid")
    checksum:str=Field(min_length=64,max_length=64)
    confirmed:bool=False

@router.post("/approvals/{id}/confirm")
async def confirm(id:str,data:Confirmation):
    if data.confirmed is not True:raise ValueError("Explicit confirmation is required.")
    return await bus.confirm(id,data.checksum)

@router.post("/approvals/{id}/reject")
def reject(id:str):
    return bus.reject_request(id)

@router.post("/request")
async def request_action(data:bus.Action):
    plan=bus.Plan(actions=[data])
    # GUI and terminal share the identical permission engine.
    async with bus.BUS_LOCK:return await bus.execute_plan(plan,None,lambda event:None)
