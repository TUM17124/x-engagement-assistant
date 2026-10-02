"""SIWC inference uses the public Responses API, not ChatGPT private endpoints."""
import json
import time
from contextvars import ContextVar
import httpx
from .providers import AIProvider
from .chatgpt_auth import auth, ChatGPTError, RESOURCE
from . import database as db

STREAM_SINK = ContextVar("ai_stream_sink", default=None)

def emit_delta(text):
    sink = STREAM_SINK.get()
    if sink and text: sink({"type":"delta","text":text})

def failure(status=0, payload=None, request_id=""):
    payload = payload if isinstance(payload,dict) else {}
    error = payload.get("error") or {}
    if not isinstance(error,dict): error={}
    code = str(error.get("code",""))[:100]
    state, message, blocked, wait = "Temporary service error", "ChatGPT is temporarily unavailable. Retry later.", False, 60
    if code == "subscription_sharing_usage_limit_exceeded" or status == 429:
        state, message, blocked, wait = "Usage limit reached", "Available ChatGPT-plan usage is exhausted or limited for this app. Manage ChatGPT Usage, then Retry. No other billing provider was used.", True, 0
    elif code in {"subscription_sharing_user_not_eligible","chatpass_v2_scope_not_authorized","chatpass_v2_invalid_authorization_context"} or status==403:
        state,message,blocked,wait = "Plan usage disabled","This ChatGPT account, workspace, or policy does not permit this request. Check plan permission or reconnect.",True,0
    elif status==401 or code=="subscription_sharing_invalid_user":
        state,message,blocked,wait = "Authorization expired","ChatGPT connection needs to be renewed. Reconnect in AI settings.",True,0
    elif code=="subscription_sharing_unsupported_capability" or status in {400,404}:
        state,message,blocked,wait = "Model unavailable","This model or requested capability is unavailable. Refresh the model catalog and select an available model.",True,0
    auth._state(state,message,blocked,wait)
    # Shape/code/request ID are useful diagnostics; provider prose can contain private input.
    db.set_setting("chatgpt_diagnostic",{"status":status,"code":code,"param":str(error.get("param",""))[:80],
        "request_id":str(request_id)[:150],"shape":"error" if error else "detail" if "detail" in payload else "other"})
    raise ChatGPTError(message,state,code,status)

class ChatGPTPlanProvider(AIProvider):
    def __init__(self, model="", key="", base_url=""):
        super().__init__(model,"",RESOURCE)

    async def get_models(self):
        token = await auth.get_access_token_for_internal_use()
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(RESOURCE+"/models",headers={"Authorization":"Bearer "+token})
        except httpx.RequestError:
            failure()
        if response.status_code != 200:
            try: payload=response.json()
            except ValueError: payload={}
            failure(response.status_code,payload,response.headers.get("x-request-id",""))
        models = [{"slug":m["slug"],"display_name":m.get("display_name",m["slug"])}
            for m in response.json().get("models",[]) if m.get("visibility")=="list" and isinstance(m.get("slug"),str)]
        db.set_setting("chatgpt_models",models)
        return models

    async def health_check(self):
        models=await self.get_models()
        if self.model and self.model not in {m["slug"] for m in models}:
            raise ValueError("Select a model from this ChatGPT account's available models.")
        return True

    async def stream(self, system, user):
        models=db.get_setting("chatgpt_models",[])
        if not models: models=await self.get_models()
        if not self.model or self.model not in {m["slug"] for m in models}:
            raise ValueError("Choose an available ChatGPT model in AI Settings.")
        token=await auth.get_access_token_for_internal_use()
        owner=auth._load()["active"]
        completed=False
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(120,connect=20)) as client:
                async with client.stream("POST",RESOURCE+"/responses",headers={"Authorization":"Bearer "+token},
                    json={"model":self.model,"instructions":system,
                          "input":[{"role":"user","content":user}],"store":False,"stream":True}) as response:
                    if response.status_code != 200:
                        await response.aread()
                        try: payload=response.json()
                        except ValueError: payload={}
                        failure(response.status_code,payload,response.headers.get("x-request-id",""))
                    data=[]
                    async for line in response.aiter_lines():
                        selected,record=auth._selected()
                        if selected["active"]!=owner or not record.get("access_token"):
                            raise ChatGPTError("ChatGPT account changed or disconnected. The response was stopped.")
                        if len(line)>1000000: raise ChatGPTError("ChatGPT returned an oversized stream event.")
                        if line.startswith("data:"):
                            data.append(line[5:].lstrip())
                        elif line=="" and data:
                            raw="\n".join(data);data=[]
                            if raw=="[DONE]":continue
                            try:event=json.loads(raw)
                            except ValueError:raise ChatGPTError("ChatGPT returned an invalid stream.") from None
                            kind=event.get("type")
                            if kind=="response.output_text.delta":
                                text=event.get("delta","")
                                if not isinstance(text,str):raise ChatGPTError("ChatGPT returned invalid output.")
                                yield text
                            elif kind=="response.completed":
                                completed=True
                            elif kind in {"response.failed","error"}:
                                failure(response.status_code,event.get("response",event),response.headers.get("x-request-id",""))
                            elif kind=="response.incomplete":
                                raise ChatGPTError("ChatGPT's response was incomplete. No draft or action was saved.")
            if not completed:
                raise ChatGPTError("ChatGPT's response was interrupted. No draft or action was saved.")
        except httpx.RequestError:
            failure()

    async def complete(self, system, user):
        parts=[]
        async for text in self.stream(system,user):
            parts.append(text);emit_delta(text)
            if sum(map(len,parts))>100000:raise ChatGPTError("ChatGPT output exceeded the local safety limit.")
        result="".join(parts).strip()
        if not result:raise ChatGPTError("ChatGPT completed without usable text.")
        return result
