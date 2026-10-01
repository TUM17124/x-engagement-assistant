import asyncio
import json
import sys
import tempfile
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch,AsyncMock
import httpx
from support import AppTest,vault,db,prefs,storage,x_api
from app.providers import GeminiProvider,OpenAIProvider,OpenAICompatibleProvider,OllamaProvider,provider
from app.secrets import SecretStore
from app.errors import ServiceError

class SecureConfigurationTests(AppTest):
    def test_secrets_masked_retrievable_and_not_in_database(self):
        key="local-test-key-abcd"
        self.client.put("/api/secrets/ai_api_key",json={"value":key})
        settings=self.client.get("/api/settings").json()
        self.assertNotIn(key,json.dumps(settings))
        self.assertTrue(settings["secrets"]["ai_api_key"].endswith("abcd"))
        self.assertEqual(self.post("/api/secrets/ai_api_key/reveal").json()["value"],key)
        self.assertNotIn(key.encode(),db.DB_PATH.read_bytes())
        self.client.delete("/api/secrets/ai_api_key")
        self.assertEqual(self.post("/api/secrets/ai_api_key/reveal").json()["value"],"")

    def test_keys_are_separate_for_each_provider(self):
        self.client.put("/api/secrets/ai_api_key",json={"value":"gemini-test-key"})
        self.client.put("/api/settings",json={"ai_provider":"openai"})
        self.assertEqual(self.post("/api/secrets/ai_api_key/reveal").json()["value"],"")
        self.client.put("/api/secrets/ai_api_key",json={"value":"openai-test-key"})
        self.client.put("/api/settings",json={"ai_provider":"gemini"})
        self.assertEqual(self.post("/api/secrets/ai_api_key/reveal").json()["value"],"gemini-test-key")

    def test_oauth_tokens_never_in_sqlite(self):
        storage.save_tokens("private-access-token","private-refresh-token",9999999999)
        self.assertEqual(storage.load_tokens()["access_token"],"private-access-token")
        self.assertNotIn(b"private-access-token",db.DB_PATH.read_bytes())
        storage.clear_tokens()
        self.assertIsNone(storage.load_tokens())

    def test_setting_validation_and_no_plaintext_secret_fields(self):
        for data in [{"ai_api_key":"no"},{"never_auto_reply":False},{"require_approval":False},
                     {"poll_minutes":1},{"daily_search_limit":0},{"ai_base_url":"http://remote.example"},
                     {"ai_base_url":"https://user:password@example.com"},{"x_redirect_uri":"https://evil.test/callback"}]:
            with self.subTest(data=data):
                self.assertEqual(self.client.put("/api/settings",json=data).status_code,400)
        self.assertEqual(self.post("/api/secrets/oauth_tokens/reveal").status_code,404)

    def test_cross_origin_mutations_and_private_desktop_control_rejected(self):
        self.assertEqual(self.client.put("/api/settings",json={"theme":"dim"},headers={"Origin":"https://evil.test"}).status_code,403)
        self.assertEqual(self.client.get("/desktop/state").status_code,403)
        self.assertEqual(self.post("/desktop/shutdown").status_code,403)

    @skipUnless(sys.platform=="win32","Windows DPAPI test")
    def test_dpapi_ciphertext_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            store=SecretStore(Path(folder))
            value="private-dpapi-test-value"
            store.set("key",value)
            self.assertEqual(store.get("key"),value)
            self.assertNotIn(value.encode(),next(Path(folder).glob("*.bin")).read_bytes())
            store.delete("key")
            self.assertEqual(store.get("key"),"")

    def test_oauth_pkce_and_scopes_preserved(self):
        from urllib.parse import urlsplit,parse_qs
        prefs.save({"x_client_id":"test-client"})
        verifier,challenge=x_api.make_pkce()
        query=parse_qs(urlsplit(x_api.make_authorize_url("state",challenge)).query)
        self.assertEqual(query["code_challenge_method"],["S256"])
        self.assertIn("tweet.write",query["scope"][0])
        self.assertGreater(len(verifier),40)
        self.assertEqual(query["redirect_uri"],["http://127.0.0.1:8787/auth/callback"])

class ProviderTests(AppTest):
    def response(self,payload,status=200):
        return httpx.Response(status,json=payload,request=httpx.Request("POST","https://provider.test"))

    def test_gemini_native_payload_and_response(self):
        response=self.response({"candidates":[{"content":{"parts":[{"text":"A specific reply."}]}}]})
        with patch.object(httpx.AsyncClient,"request",new_callable=AsyncMock,return_value=response) as call:
            text=asyncio.run(GeminiProvider("test-model","test-key").generate_reply({"text":"PDF notes","username":"reader"}))
            self.assertEqual(text,"A specific reply.")
            self.assertEqual(call.call_args.kwargs["headers"]["x-goog-api-key"],"test-key")
            self.assertIn(":generateContent",call.call_args.args[1])
            payload=call.call_args.kwargs["json"]
            self.assertIn("Do not force product mentions",payload["systemInstruction"]["parts"][0]["text"])
            self.assertNotIn("test-key",json.dumps(payload))

    def test_openai_compatible_payload_and_abstraction(self):
        response=self.response({"choices":[{"message":{"content":"Useful draft"}}]})
        with patch.object(httpx.AsyncClient,"request",new_callable=AsyncMock,return_value=response) as call:
            p=OpenAICompatibleProvider("configured-model","test-key","https://provider.test/v1")
            self.assertEqual(asyncio.run(p.generate_post("My useful idea")),"Useful draft")
            self.assertEqual(call.call_args.args[1],"https://provider.test/v1/chat/completions")
            self.assertEqual(call.call_args.kwargs["json"]["model"],"configured-model")
        for name,cls in [("gemini",GeminiProvider),("openai",OpenAIProvider),("compatible",OpenAICompatibleProvider),("ollama",OllamaProvider)]:
            prefs.save({"ai_provider":name})
            self.assertIsInstance(provider(),cls)

    def test_ollama_payload(self):
        response=self.response({"message":{"content":"Local reply"}})
        with patch.object(httpx.AsyncClient,"request",new_callable=AsyncMock,return_value=response) as call:
            p=OllamaProvider("local-model","","http://127.0.0.1:11434")
            self.assertEqual(asyncio.run(p.rewrite("text","shorter")),"Local reply")
            self.assertFalse(call.call_args.kwargs["json"]["stream"])
            self.assertNotIn("headers",call.call_args.kwargs)

    def test_health_and_invalid_keys_no_key_leak(self):
        for status in [401,402,403,429]:
            with self.subTest(status=status):
                response=self.response({"error":"sensitive-provider-body"},status)
                with patch.object(httpx.AsyncClient,"request",new_callable=AsyncMock,return_value=response):
                    with self.assertRaises(ServiceError) as error:
                        asyncio.run(GeminiProvider("model","private-api-key").health_check())
                    self.assertNotIn("private-api-key",str(error.exception))
                    self.assertNotIn("sensitive-provider-body",str(error.exception))
                    self.assertEqual(error.exception.status,status)

    def test_x_401_402_403_429(self):
        storage.save_tokens("fake-token",None,9999999999)
        for status in [401,402,403,429]:
            with self.subTest(status=status):
                with patch.object(httpx.AsyncClient,"request",new_callable=AsyncMock,return_value=self.response({},status)):
                    with self.assertRaises(ServiceError) as error:
                        asyncio.run(x_api.read_endpoint("/tweets/search/recent",{"query":"test"}))
                    self.assertEqual(error.exception.status,status)
                    if status==402:self.assertIn("credits/access",str(error.exception))

    def test_empty_provider_response_is_clear_error(self):
        with patch.object(httpx.AsyncClient,"request",new_callable=AsyncMock,return_value=self.response({"choices":[]})):
            with self.assertRaises(ValueError):
                asyncio.run(OpenAICompatibleProvider("model","","https://test.example").complete("system","user"))
