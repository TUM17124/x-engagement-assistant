"""Official provider protocols. Product features consume GenerationResult, never wire JSON."""
from dataclasses import dataclass, field
import json, time
from urllib.parse import quote
import httpx
from .ai_base import AIProvider
from .ai_registry import CATALOG, validate_url
from .errors import ServiceError, check_response

async def request(client,method,url,service,**kwargs):
    try:response=await client.request(method,url,**kwargs)
    except httpx.TimeoutException:raise ServiceError(service,408) from None
    except httpx.RequestError:raise ServiceError(service) from None
    if 300<=response.status_code<400:raise ValueError("Provider redirected the request. Credentials were not forwarded; verify the configured endpoint.")
    try:check_response(response,service)
    except ServiceError as error:
        try:
            body=response.json(); item=body.get("error") or {}; code=item.get("code","") if isinstance(item,dict) else ""
            error.billing=code in {"insufficient_quota","billing_hard_limit_reached","credit_balance_exhausted","insufficient_balance"}
            if error.billing: error.status=402; error.args=("Your AI provider reports a billing or credit problem. Check its billing page.",)
        except (ValueError,TypeError,AttributeError):pass
        raise
    return response

@dataclass
class GenerationRequest:
    system: str
    user: str
    image: str = ""  # local base64 JPEG, never an arbitrary fetch URL
    json_output: bool = False
    schema: dict | None = None

@dataclass
class GenerationResult:
    text: str
    provider: str
    model: str
    usage: dict = field(default_factory=dict)
    finish_reason: str = ""
    request_id: str = ""


def text_parts(parts):
    if isinstance(parts,str): return parts
    return "".join(p.get("text", "") for p in parts or [] if isinstance(p,dict) and p.get("type","text") in {"text","output_text"} and not p.get("thought"))

def model_info(m):
    ident = m.get("id") or m.get("name") or m.get("model")
    if not isinstance(ident,str): return None
    arch=m.get("architecture") or {}; caps=m.get("capabilities") or {}
    caps={k:(v.get("supported") if isinstance(v,dict) else v) for k,v in caps.items()} if isinstance(caps,dict) else {}
    params=m.get("supported_parameters")
    if isinstance(params,list):caps["structured_outputs"]="structured_outputs" in params or "response_format" in params
    inputs=m.get("input_modalities",arch.get("input_modalities")); outputs=m.get("output_modalities",arch.get("output_modalities"))
    return {"id":ident.removeprefix("models/"), "name":m.get("display_name",m.get("displayName",ident)),
        "context_window":m.get("context_window",m.get("context_length",m.get("max_context_length",m.get("inputTokenLimit")))),
        "input_capabilities":inputs,"output_capabilities":outputs,
        "vision":("image" in inputs) if inputs is not None else caps.get("vision"),
        "reasoning":bool(m["effort"].get("supported_levels")) if isinstance(m.get("effort"),dict) else caps.get("reasoning",caps.get("thinking")),
        "structured_output":caps.get("structured_outputs"),
        "status":"deprecated" if m.get("is_deprecated") else m.get("status"),
        "pricing":m.get("pricing"),"aliases":m.get("aliases")}

class WireProvider(AIProvider):
    kind="compatible"
    def __init__(self,model,key="",base_url=""):
        meta=CATALOG[self.kind]
        base = base_url or meta["base_url"] if self.kind in {"compatible","ollama","lmstudio"} else meta["base_url"]
        super().__init__(model,key,validate_url(base) if base else "")
        self.service=meta["name"]; self.feature="default"; self.managed=False; self.allow_fallback=True
        self.last_result=None
    def headers(self): return {"Authorization":"Bearer "+self.key} if self.key else {}
    def endpoint(self,stream=False): return self.base_url+"/chat/completions"
    def payload(self,r,stream=False):
        content=r.user if not r.image else [{"type":"text","text":r.user},{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+r.image}}]
        p={"model":self.model,"messages":[{"role":"system","content":r.system},{"role":"user","content":content}],"stream":stream,"max_tokens":4096}
        if self.kind=="groq":p["max_completion_tokens"]=p.pop("max_tokens")
        if r.json_output:p["response_format"]={"type":"json_object"}
        return p
    def result(self,data):
        c=data["choices"][0]
        return GenerationResult(text_parts(c["message"]["content"]),self.kind,data.get("model",self.model),data.get("usage") or {},c.get("finish_reason") or "",data.get("id", ""))
    def delta(self,d):
        c=(d.get("choices") or [{}])[0]
        return text_parts(c.get("delta",{}).get("content")),bool(c.get("finish_reason")),d.get("usage") or {},c.get("finish_reason") or ""
    async def preflight(self):
        if not self.base_url:raise ValueError("Configure an AI endpoint in Settings > AI Providers.")
        if not self.model:raise ValueError("Select an AI model in Settings > AI Providers.")
        if self.managed:
            from .ai_connections import enforce_local
            await enforce_local(self)
    async def list_models(self):
        if self.kind=="openrouter":
            async with httpx.AsyncClient(timeout=20,follow_redirects=False) as client:
                await request(client,"GET",self.base_url+"/key",self.service,headers=self.headers())
        path=CATALOG[self.kind]["models_path"]; output=[]; params={}
        async with httpx.AsyncClient(timeout=20,follow_redirects=False) as client:
            for page in range(20):
                kwargs={"params":params}
                if self.headers():kwargs["headers"]=self.headers()
                response=await request(client,"GET",self.base_url+path,self.service,**kwargs)
                try:
                    data=response.json()
                    items=data if isinstance(data,list) else data.get("data",data.get("models"))
                    if not isinstance(items,list):raise ValueError()
                    for m in items:
                        if not isinstance(m,dict):continue
                        if isinstance(m.get("capabilities"),dict) and m["capabilities"].get("completion_chat") is False:continue
                        if m.get("is_deprecated") or m.get("type") in {"embedding","audio","image","rerank"}:continue
                        if "supportedGenerationMethods" in m and "generateContent" not in m["supportedGenerationMethods"]:continue
                        if "endpoints" in m and "chat" not in m["endpoints"]:continue
                        info=model_info(m)
                        if info:output.append(info)
                    if not isinstance(data,dict):break
                    token=data.get("nextPageToken") or data.get("next_page_token")
                    if token:params={"pageToken" if self.kind=="gemini" else "page_token":token}
                    elif data.get("has_more") and data.get("last_id"):params={"after_id":data["last_id"]}
                    else:break
                except (ValueError,TypeError,KeyError,AttributeError):raise ValueError("Provider returned an invalid model catalog. No configuration was changed.") from None
            else:raise ValueError("Model catalog pagination limit reached. Narrow the provider catalog.")
        return output
    async def health_check(self):
        models=await self.list_models()
        if self.model and self.model not in {m["id"] for m in models}:raise ValueError("The selected model is not available to this connection. Refresh Models and choose an available model.")
        return True
    async def generate(self,r):
        await self.preflight(); started=time.monotonic(); result=None
        metadata=getattr(self,"model_metadata",{})
        if r.image and metadata.get("vision") is False:raise ValueError("This model does not support image input. Choose a vision model.")
        if metadata.get("structured_output") is False:
            from dataclasses import replace
            r=replace(r,json_output=False,schema=None)
        try:
            if self.managed:
                from . import database as db
                state=db.get_setting("ai_backoff_"+self.kind,{})
                if state.get("until",0)>time.time():
                    error=ServiceError(self.service,state.get("status",429),retry_after=int(state["until"]-time.time()))
                    error.cached=True
                    raise error
            async with httpx.AsyncClient(timeout=120,follow_redirects=False) as client:
                kwargs={"json":self.payload(r)}
                if self.headers():kwargs["headers"]=self.headers()
                response=await request(client,"POST",self.endpoint(),self.service,**kwargs)
            try:
                result=self.result(response.json()); result.text=result.text.strip()
                if not result.text or result.finish_reason.lower() in {"length","max_tokens","max_output_tokens","incomplete","error","aborted","content_filter","safety"}:raise ValueError()
            except (ValueError,KeyError,IndexError,TypeError,AttributeError):
                raise ValueError("The AI returned no usable text or a malformed response. Check the selected model and try again.") from None
            self.last_result=result
            return result
        except ServiceError as error:
            if self.managed and not getattr(error,"cached",False) and (error.status==429 or 500<=error.status<=599):
                from . import database as db
                db.set_setting("ai_backoff_"+self.kind,{"status":error.status,"until":time.time()+max(error.retry_after,60)})
            if self.managed and self.allow_fallback:
                from .ai_connections import fallback_provider
                alternate=fallback_provider(self,error)
                if alternate:
                    self.last_result=await alternate.generate(r)
                    return self.last_result
            raise
        finally:
            if self.managed:
                from .ai_connections import record_request
                record_request(self,r,result,started)
    async def complete(self,system,user):
        from .chatgpt_provider import STREAM_SINK
        if STREAM_SINK.get():
            chunks=[]
            async for chunk in self.stream(system,user):
                chunks.append(chunk);STREAM_SINK.get()({"type":"delta","text":chunk})
            return "".join(chunks).strip()
        return (await self.generate(GenerationRequest(system,user))).text
    async def structured_reply(self,system,user):
        schema={"type":"object","properties":{"reply":{"type":"string"},"reason":{"type":"string"},"score":{"type":"integer","minimum":0,"maximum":100},"topic":{"type":"string"}},"required":["reply","reason","score","topic"],"additionalProperties":False}
        return (await self.generate(GenerationRequest(system,user,json_output=self.kind!="compatible",schema=schema))).text
    async def analyze(self,system,user):
        result=await self.generate(GenerationRequest(system,user,json_output=self.kind not in {"compatible","chatgpt"}))
        try:return json.loads(result.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```"))
        except (ValueError,TypeError):raise ValueError("The AI did not return valid structured data. No action was taken.") from None
    async def vision(self,prompt,image):return (await self.generate(GenerationRequest("Describe only visible details. Never invent claims or identify people.",prompt,image))).text
    async def stream(self,system,user):
        await self.preflight();r=GenerationRequest(system,user);started=time.monotonic();completed=False;text=[];usage={};finish="";result=None
        try:
            async with httpx.AsyncClient(timeout=120,follow_redirects=False) as client:
                async with client.stream("POST",self.endpoint(True),headers=self.headers(),json=self.payload(r,True)) as response:
                    check_response(response,self.service)
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):line=line[5:].strip()
                        elif self.kind!="ollama":continue
                        if not line or line=="[DONE]":continue
                        try:
                            data=json.loads(line)
                            if data.get("error") or data.get("type") in {"error","response.failed"}:raise ServiceError(self.service,502)
                            chunk,done,tokens,reason=self.delta(data)
                            completed=completed or done;usage.update(tokens);finish=reason or finish
                            if chunk:text.append(chunk);yield chunk
                        except (ValueError,KeyError,IndexError,TypeError,AttributeError):raise ValueError("AI stream returned invalid data. Partial output was not saved.") from None
            if not completed or not "".join(text).strip() or finish.lower() in {"length","max_tokens","max_output_tokens","incomplete","error","aborted","content_filter","safety"}:raise ValueError("AI stream was interrupted. Partial output was not saved.")
            result=GenerationResult("".join(text),self.kind,self.model,usage,finish)
            self.last_result=result
        except httpx.RequestError:raise ServiceError(self.service) from None
        finally:
            if self.managed:
                from .ai_connections import record_request
                record_request(self,r,result,started)

class OpenAICompatibleProvider(WireProvider):pass
class GroqProvider(WireProvider):kind="groq"
class MistralProvider(WireProvider):kind="mistral"
class DeepSeekProvider(WireProvider):kind="deepseek"
class KimiProvider(WireProvider):kind="kimi"
class OpenRouterProvider(WireProvider):kind="openrouter"
class TogetherProvider(WireProvider):kind="together"
class LMStudioProvider(WireProvider):kind="lmstudio"

class ResponsesProvider(WireProvider):
    def endpoint(self,stream=False):return self.base_url+"/responses"
    def payload(self,r,stream=False):
        content=r.user if not r.image else [{"type":"input_text","text":r.user},{"type":"input_image","image_url":"data:image/jpeg;base64,"+r.image}]
        p={"model":self.model,"input":[{"role":"system","content":r.system},{"role":"user","content":content}],"store":False,"stream":stream}
        if r.json_output:p["text"]={"format":{"type":"json_object"}}
        return p
    def result(self,d):return GenerationResult("".join(text_parts(x.get("content")) for x in d.get("output",[]) if x.get("type")=="message"),self.kind,d.get("model",self.model),d.get("usage") or {},d.get("status", ""),d.get("id",""))
    def delta(self,d):
        response=d.get("response") or {}
        return d.get("delta","") if d.get("type")=="response.output_text.delta" else "",d.get("type")=="response.completed",response.get("usage") or {},response.get("status","")
class OpenAIProvider(ResponsesProvider):kind="openai"
class XAIProvider(ResponsesProvider):kind="grok"
GrokProvider=XAIProvider

class GeminiProvider(WireProvider):
    kind="gemini"
    def headers(self):return {"x-goog-api-key":self.key}
    def endpoint(self,stream=False):return self.base_url+"/models/"+quote(self.model.removeprefix("models/"),safe="")+(":streamGenerateContent?alt=sse" if stream else ":generateContent")
    def payload(self,r,stream=False):
        parts=[{"text":r.user}]
        if r.image:parts.append({"inlineData":{"mimeType":"image/jpeg","data":r.image}})
        config={"maxOutputTokens":4096}
        if r.json_output:config["responseMimeType"]="application/json"
        return {"systemInstruction":{"parts":[{"text":r.system}]},"contents":[{"role":"user","parts":parts}],"generationConfig":config}
    def result(self,d):
        c=d["candidates"][0];u=d.get("usageMetadata") or {}
        return GenerationResult(text_parts(c["content"]["parts"]),self.kind,d.get("modelVersion",self.model),{"input_tokens":u.get("promptTokenCount"),"output_tokens":u.get("candidatesTokenCount")},c.get("finishReason", ""),d.get("responseId", ""))
    def delta(self,d):
        c=(d.get("candidates") or [{}])[0];u=d.get("usageMetadata") or {}
        return text_parts(c.get("content",{}).get("parts")),bool(c.get("finishReason")),{"input_tokens":u.get("promptTokenCount"),"output_tokens":u.get("candidatesTokenCount")},c.get("finishReason", "")

class AnthropicProvider(WireProvider):
    kind="claude"
    def headers(self):
        from . import preferences as prefs
        h={"Authorization":"Bearer "+self.key,"anthropic-version":"2023-06-01"}
        if prefs.get("claude_workspace_id"):h["anthropic-workspace-id"]=prefs.get("claude_workspace_id")
        return h
    def endpoint(self,stream=False):return self.base_url+"/messages"
    def payload(self,r,stream=False):
        content=[{"type":"text","text":r.user}]
        if r.image:content.append({"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":r.image}})
        p={"model":self.model,"system":r.system+(" Return valid JSON only." if r.json_output else ""),"messages":[{"role":"user","content":content}],"max_tokens":4096,"stream":stream}
        if r.schema and getattr(self,"model_metadata",{}).get("structured_output") is True:p["output_config"]={"format":{"type":"json_schema","schema":r.schema}}
        return p
    def result(self,d):return GenerationResult(text_parts(d["content"]),self.kind,d.get("model",self.model),d.get("usage") or {},d.get("stop_reason", ""),d.get("id", ""))
    def delta(self,d):
        delta=d.get("delta") or {};usage=d.get("usage") or d.get("message",{}).get("usage") or {}
        return delta.get("text","") if delta.get("type")=="text_delta" else "",d.get("type")=="message_stop",usage,delta.get("stop_reason", "")
ClaudeProvider=AnthropicProvider

class CohereProvider(WireProvider):
    kind="cohere"
    def endpoint(self,stream=False):return self.base_url+"/v2/chat"
    def payload(self,r,stream=False):return super().payload(r,stream)
    def result(self,d):return GenerationResult(text_parts(d["message"]["content"]),self.kind,self.model,(d.get("usage") or {}).get("tokens") or {},d.get("finish_reason", ""),d.get("id", ""))
    def delta(self,d):
        delta=d.get("delta") or {};message=delta.get("message") or {}
        return (message.get("content") or {}).get("text", ""),d.get("type")=="message-end",(delta.get("usage") or {}).get("tokens") or {},delta.get("finish_reason", "")

class OllamaProvider(WireProvider):
    kind="ollama"
    def endpoint(self,stream=False):return self.base_url+"/api/chat"
    def payload(self,r,stream=False):
        msg={"role":"user","content":r.user}
        if r.image:msg["images"]=[r.image]
        p={"model":self.model,"messages":[{"role":"system","content":r.system},msg],"stream":stream,"options":{"num_predict":4096}}
        if r.json_output:p["format"]="json"
        return p
    def result(self,d):return GenerationResult(d["message"]["content"],self.kind,d.get("model",self.model),{"input_tokens":d.get("prompt_eval_count"),"output_tokens":d.get("eval_count")},d.get("done_reason", ""))
    def delta(self,d):return d.get("message",{}).get("content", ""),bool(d.get("done")),{"input_tokens":d.get("prompt_eval_count"),"output_tokens":d.get("eval_count")},d.get("done_reason", "")

ADAPTERS={cls.kind:cls for cls in [OpenAICompatibleProvider,GroqProvider,MistralProvider,DeepSeekProvider,KimiProvider,OpenRouterProvider,TogetherProvider,LMStudioProvider,OpenAIProvider,XAIProvider,GeminiProvider,AnthropicProvider,CohereProvider,OllamaProvider]}
