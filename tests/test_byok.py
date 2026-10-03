import asyncio, json, time
from unittest.mock import patch, AsyncMock
import httpx
from support import AppTest, db, prefs, vault
from app.ai_adapters import ADAPTERS, GenerationRequest, model_info
from app import ai_connections as ai
from app.ai_registry import CATALOG, validate_url
from app.errors import ServiceError

class BYOKTests(AppTest):
    def response(self,data,status=200):return httpx.Response(status,json=data,request=httpx.Request("GET","https://provider.test"))
    def payload(self,kind):
        wire=CATALOG[kind]["wire"]
        if wire=="gemini":return {"candidates":[{"content":{"parts":[{"text":"Draft"}]},"finishReason":"STOP"}],"usageMetadata":{"promptTokenCount":2,"candidatesTokenCount":1}}
        if wire=="messages":return {"content":[{"type":"text","text":"Draft"}],"usage":{"input_tokens":2,"output_tokens":1},"stop_reason":"end_turn"}
        if wire=="responses":return {"output":[{"type":"message","content":[{"type":"output_text","text":"Draft"}]}],"usage":{"input_tokens":2,"output_tokens":1},"status":"completed"}
        if wire=="cohere":return {"message":{"content":[{"type":"text","text":"Draft"}]},"usage":{"tokens":{"input_tokens":2,"output_tokens":1}},"finish_reason":"COMPLETE"}
        if wire=="ollama":return {"message":{"content":"Draft"},"prompt_eval_count":2,"eval_count":1,"done":True}
        return {"choices":[{"message":{"content":"Draft"},"finish_reason":"stop"}],"usage":{"prompt_tokens":2,"completion_tokens":1}}
    def instance(self,kind):return ADAPTERS[kind]("model","secret-test-key",CATALOG[kind]["base_url"] or "https://custom.test/v1")
    def test_all_adapters_normalize_generation_and_errors(self):
        for kind in ADAPTERS:
            with self.subTest(provider=kind):
                model=self.instance(kind)
                with patch.object(httpx.AsyncClient,"request",AsyncMock(return_value=self.response(self.payload(kind)))) as call:
                    result=asyncio.run(model.generate(GenerationRequest("Trusted rules","Untrusted social post")))
                    self.assertEqual(result.text,"Draft");self.assertEqual(result.provider,kind);self.assertTrue(result.usage)
                    self.assertNotIn(model.key,json.dumps(call.call_args.kwargs["json"]))
                for status in (400,401,402,403,404,408,429,500,503):
                    with patch.object(httpx.AsyncClient,"request",AsyncMock(return_value=self.response({"error":{"message":"private prompt secret-test-key"}},status))):
                        with self.assertRaises(ServiceError) as error:asyncio.run(model.generate(GenerationRequest("s","u")))
                        self.assertEqual(error.exception.status,status);self.assertNotIn("secret-test-key",str(error.exception))
                with patch.object(httpx.AsyncClient,"request",AsyncMock(side_effect=httpx.ReadTimeout("secret-test-key"))):
                    with self.assertRaises(ServiceError) as error:asyncio.run(model.complete("s","u"))
                    self.assertEqual(error.exception.status,408);self.assertNotIn("secret-test-key",str(error.exception))
                for malformed in ({},[],{"choices":[{"message":{"content":None}}]}):
                    with patch.object(httpx.AsyncClient,"request",AsyncMock(return_value=self.response(malformed))):
                        with self.assertRaises(ValueError):asyncio.run(model.complete("s","u"))
    def test_all_adapters_model_listing(self):
        for kind in ADAPTERS:
            wire=CATALOG[kind]["wire"]
            body={"data":[{"id":"model","context_length":8192}]}
            if kind=="gemini":body={"models":[{"name":"models/model","supportedGenerationMethods":["generateContent"],"inputTokenLimit":8192}]}
            if kind=="cohere":body={"models":[{"name":"model","endpoints":["chat"],"context_length":8192}]}
            if kind=="ollama":body={"models":[{"name":"model"}]}
            if kind=="together":body=body["data"]
            with self.subTest(provider=kind),patch.object(httpx.AsyncClient,"request",AsyncMock(return_value=self.response(body))):
                models=asyncio.run(self.instance(kind).list_models());self.assertEqual(models[0]["id"],"model")
                self.assertIsNone(models[0]["vision"])
    def stream_events(self,kind):
        wire=CATALOG[kind]["wire"]
        if wire=="gemini":return [{"candidates":[{"content":{"parts":[{"text":"Draft"}]},"finishReason":"STOP"}]}]
        if wire=="messages":return [{"type":"content_block_delta","delta":{"type":"text_delta","text":"Draft"}},{"type":"message_stop"}]
        if wire=="responses":return [{"type":"response.output_text.delta","delta":"Draft"},{"type":"response.completed","response":{"status":"completed"}}]
        if wire=="cohere":return [{"type":"content-delta","delta":{"message":{"content":{"text":"Draft"}}}},{"type":"message-end","delta":{"finish_reason":"COMPLETE"}}]
        if wire=="ollama":return [{"message":{"content":"Draft"},"done":True}]
        return [{"choices":[{"delta":{"content":"Draft"},"finish_reason":"stop"}]}]
    def test_all_adapters_stream_and_interruption(self):
        async def consume(obj):return "".join([part async for part in obj.stream("s","u")])
        for kind in ADAPTERS:
            body="\n".join(("" if kind=="ollama" else "data: ")+json.dumps(x) for x in self.stream_events(kind))+"\n"
            response=httpx.Response(200,content=body,request=httpx.Request("POST","https://provider.test"))
            with self.subTest(provider=kind),patch.object(httpx.AsyncClient,"send",AsyncMock(return_value=response)):
                self.assertEqual(asyncio.run(consume(self.instance(kind))),"Draft")
            response=httpx.Response(200,content="",request=httpx.Request("POST","https://provider.test"))
            with patch.object(httpx.AsyncClient,"send",AsyncMock(return_value=response)):
                with self.assertRaisesRegex(ValueError,"interrupted"):asyncio.run(consume(self.instance(kind)))
    def test_provider_save_secure_listing_models_activate_disable(self):
        body={"name":"Personal Groq","base_url":CATALOG["groq"]["base_url"],"model":"model","api_key":"private-byok-key"}
        with patch.object(httpx.AsyncClient,"request",AsyncMock(return_value=self.response({"data":[{"id":"model"}]}))):
            self.assertEqual(self.post("/api/ai/providers/groq/test",body).status_code,200)
            self.assertIsNone(ai.config("groq"))
            r=self.client.put("/api/ai/providers/groq",json=body);self.assertEqual(r.status_code,200,r.text)
            self.assertEqual(vault.get("ai_api_key_groq"),body["api_key"])
            self.assertNotIn(body["api_key"],self.client.get("/api/ai/providers").text)
            self.assertNotIn(body["api_key"].encode(),db.DB_PATH.read_bytes())
            self.assertEqual(self.post("/api/ai/providers/groq/activate").status_code,200)
            self.assertEqual(ai.selected_provider().kind,"groq")
            self.post("/api/ai/providers/groq/disable")
            with self.assertRaisesRegex(ValueError,"disabled"):ai.selected_provider()
        self.client.delete("/api/ai/providers/groq/key");self.assertEqual(vault.get("ai_api_key_groq"),"")
    def test_malformed_key_payload_not_echoed(self):
        r=self.client.put("/api/ai/providers/groq",json={"api_key":{"secret":"never-echo-me"},"model":[],"password":"never-echo-me"})
        self.assertEqual(r.status_code,422);self.assertNotIn("never-echo-me",r.text)
    def test_custom_endpoint_binding_and_redirects(self):
        for url in ("http://public.test/v1","https://name:password@api.test/v1","https://api.test/v1?key=x","https://api.test/#x","file:///secret"):
            with self.assertRaises(ValueError):validate_url(url)
        cfg={"model":"model","base_url":"https://custom.test/v1","name":"Custom","enabled":True,"local":False}
        db.execute("INSERT INTO ai_connections(id,config) VALUES('compatible',?)",(json.dumps(cfg),));vault.set("ai_api_key_compatible","bound-key")
        r=self.post("/api/ai/providers/compatible/test",{**cfg,"base_url":"https://other.test/v1"})
        self.assertEqual(r.status_code,400);self.network.assert_not_called()
        with patch.object(httpx.AsyncClient,"request",AsyncMock(return_value=self.response({},302))):
            with self.assertRaisesRegex(ValueError,"not forwarded"):asyncio.run(self.instance("compatible").complete("s","u"))
    def test_local_only_blocks_cloud_and_ollama_remote_alias(self):
        db.set_setting("ai_policy",{"local_only":True,"fallback_enabled":True,"fallback":"groq"})
        self.assertFalse(ai.policy().fallback_enabled)
        with self.assertRaisesRegex(ValueError,"Local AI Only"):ai.selected_provider()
        prefs.save({"ai_provider":"ollama","ai_model":"alias","ai_base_url":"http://127.0.0.1:11434"})
        model=ai.selected_provider()
        with patch.object(httpx.AsyncClient,"request",AsyncMock(return_value=self.response({"remote_host":"cloud","model_info":{}}))) as call:
            with self.assertRaisesRegex(ValueError,"Cloud or unverifiable"):asyncio.run(model.complete("s","private source"))
            self.assertEqual(call.await_count,1);self.assertNotIn("private source",str(call.call_args))
    def test_fallback_opt_in_and_no_billing_auth_fallback(self):
        db.execute("INSERT INTO ai_connections(id,config) VALUES('ollama',?)",(json.dumps({"model":"local-model","base_url":"http://127.0.0.1:11434","enabled":True,"local":True}),))
        model=self.instance("gemini");model.managed=True
        self.assertIsNone(ai.fallback_provider(model,ServiceError("Gemini",503)))
        db.set_setting("ai_policy",{"fallback_enabled":True,"fallback":"ollama"})
        for status in (401,402,403,404):self.assertIsNone(ai.fallback_provider(model,ServiceError("Gemini",status)))
        responses=[self.response({},503),self.response(self.payload("ollama"))]
        with patch.object(httpx.AsyncClient,"request",AsyncMock(side_effect=responses)):
            result=asyncio.run(model.generate(GenerationRequest("s","u")));self.assertEqual(result.provider,"ollama")
        self.assertEqual(db.one("SELECT COUNT(*) n FROM ai_requests")["n"],2)
        db.set_setting("ai_backoff_gemini",{})  # Separate scenario after an explicit retry.
        with patch.object(httpx.AsyncClient,"request",AsyncMock(return_value=self.response({"error":{"code":"insufficient_quota"}},429))) as call:
            with self.assertRaises(ServiceError) as error:asyncio.run(model.complete("s","u"))
            self.assertEqual(error.exception.status,402);self.assertEqual(call.await_count,1)
    def test_cache_refresh_context_privacy_and_feature_selection(self):
        db.execute("INSERT INTO ai_connections(id,config) VALUES('groq',?)",(json.dumps({"model":"model","base_url":CATALOG['groq']['base_url'],"enabled":True}),))
        with patch.object(httpx.AsyncClient,"request",AsyncMock(return_value=self.response({"data":[{"id":"model"}]}))) as call:
            asyncio.run(ai.models("groq"));asyncio.run(ai.models("groq"));self.assertEqual(call.await_count,1)
            asyncio.run(ai.models("groq",refresh=True));self.assertEqual(call.await_count,2)
        prefs.save({"my_profile":{"bio":"private bio"},"voice":{"tone":"private tone"},"product":{"name":"private product"}})
        db.set_setting("ai_policy",{"send_profile":False,"send_voice":False,"send_product":False,"send_conversation":False,"overrides":{"replies":"groq"},"feature_models":{"replies":"model"}})
        self.assertNotIn("private",json.dumps(ai.writing_context()));self.assertEqual(ai.selected_provider("replies").kind,"groq")
    def test_migration_preserves_keys_and_settings_after_restart(self):
        prefs.save({"ai_provider":"compatible","ai_model":"saved-model","ai_base_url":"https://api.groq.com/openai/v1"})
        vault.set("ai_api_key_compatible","migration-test-secret");db.set_setting("ai_connections_migrated",False)
        ai.migrate();self.assertEqual(prefs.get("ai_provider"),"groq");self.assertEqual(ai.config("groq")["model"],"saved-model")
        self.assertEqual(vault.get("ai_api_key_groq"),"migration-test-secret");self.assertEqual(vault.get("ai_api_key_compatible"),"migration-test-secret")
        db.init_db();ai.migrate();self.assertEqual(ai.config("groq")["model"],"saved-model")
        self.assertNotIn(b"migration-test-secret",db.DB_PATH.read_bytes())
    def test_openrouter_pkce_single_use_expiry_and_no_key_response(self):
        from app.openrouter_auth import pending
        from urllib.parse import urlsplit,parse_qs
        r=self.post("/api/ai/openrouter/connect").json();query=parse_qs(urlsplit(r["url"]).query)
        self.assertEqual(query["code_challenge_method"],["S256"]);callback=urlsplit(query["callback_url"][0]).path
        with patch.object(httpx.AsyncClient,"request",AsyncMock(return_value=self.response({"key":"private-router-key"}))):
            response=self.client.get(callback+"?code=test-code");self.assertEqual(response.status_code,200)
            self.assertNotIn("private-router-key",response.text);self.assertEqual(vault.get("ai_api_key_openrouter"),"private-router-key")
            self.assertEqual(self.client.get(callback+"?code=test-code").status_code,400)
        self.assertEqual(self.client.get("/auth/openrouter/made-up?code=test").status_code,400)

    def test_manual_custom_model_and_known_vision_schema_capabilities(self):
        from app.ai_adapters import AnthropicProvider,GenerationRequest
        obj=AnthropicProvider("model","key");obj.model_metadata={"structured_output":True}
        payload=obj.payload(GenerationRequest("rules","data",json_output=True,schema={"type":"object"}))
        self.assertEqual(payload["output_config"]["format"]["type"],"json_schema")
        obj.model_metadata={"vision":False}
        with self.assertRaises(ValueError):asyncio.run(obj.generate(GenerationRequest("rules","data",image="aGVsbG8=")))
        config={"base_url":"http://127.0.0.1:1234/v1","model":"local-model","manual_model":True,"local":True}
        with patch.object(ADAPTERS["compatible"],"complete",AsyncMock(return_value="OK")) as complete:
            r=self.post('/api/ai/providers/compatible/test',config);self.assertEqual(r.status_code,200,r.text)
            self.assertEqual(r.json()["models"][0]["id"],"local-model");complete.assert_awaited_once()
    def test_transient_backoff_does_not_hammer_primary(self):
        prefs.save({"ai_provider":"gemini","ai_model":"model"})
        obj=ai.selected_provider()
        with patch.object(httpx.AsyncClient,"request",AsyncMock(return_value=self.response({},429))) as call:
            for _ in range(2):
                with self.assertRaises(ServiceError):asyncio.run(obj.complete("s","u"))
            call.assert_awaited_once()

    def test_model_capabilities_survive_save_and_unconfigured_settings_roundtrip(self):
        prefs.save({"ai_provider":""});prefs.save(prefs.all_settings(),persist=False)
        with patch.object(ADAPTERS["claude"],"list_models",AsyncMock(return_value=[{"id":"model","name":"Model","structured_output":True}])):
            r=self.client.put('/api/ai/providers/claude',json={"model":"model","api_key":"sample-key"});self.assertEqual(r.status_code,200,r.text)
        self.assertTrue(ai.build("claude").model_metadata["structured_output"])
