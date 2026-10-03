import asyncio,json
from unittest.mock import patch,AsyncMock
import httpx
from support import AppTest,prefs,vault,db
from app.providers import provider,GrokProvider,ClaudeProvider,KimiProvider,DeepSeekProvider
from app.errors import ServiceError
from app.command_bus import redact

class ExtraProviderTests(AppTest):
    def response(self,body,status=200):return httpx.Response(status,json=body,request=httpx.Request('POST','https://api.example'))
    def test_native_grok_and_claude_payloads(self):
        cases=[(GrokProvider,{'output':[{'type':'message','content':[{'type':'output_text','text':'Useful response'}]}]},'/responses'),
               (ClaudeProvider,{'content':[{'type':'text','text':'Useful response'}]},'/messages')]
        for cls,body,path in cases:
            with patch.object(httpx.AsyncClient,'request',AsyncMock(return_value=self.response(body))) as request:
                self.assertEqual(asyncio.run(cls('chosen-model','test-secret').complete('Instructions','Untrusted source')),'Useful response')
                self.assertTrue(request.call_args.args[1].endswith(path))
                payload=request.call_args.kwargs['json'];self.assertEqual(payload['model'],'chosen-model')
                self.assertNotIn('test-secret',json.dumps(payload))
                if cls is ClaudeProvider:self.assertEqual(payload['system'],'Instructions')
                else:self.assertEqual(payload['input'][0]['role'],'system')
    def test_compatible_kimi_deepseek_and_fixed_endpoints(self):
        for cls,host in [(KimiProvider,'https://api.moonshot.ai/v1'),(DeepSeekProvider,'https://api.deepseek.com')]:
            body={'choices':[{'message':{'content':'A thoughtful answer'}}]}
            with patch.object(httpx.AsyncClient,'request',AsyncMock(return_value=self.response(body))) as request:
                self.assertEqual(asyncio.run(cls('chosen','test-key','https://untrusted.test').complete('System','Text')),'A thoughtful answer')
                self.assertEqual(request.call_args.args[1],host+'/chat/completions')
                self.assertNotIn('temperature',request.call_args.kwargs['json'])
    def test_unknown_xai_credential_rejected_before_history(self):
        from app.command_bus import safe_input
        key='xai-'+('sample-secret-'*3)
        self.assertEqual(redact(key),'[REDACTED]')
        with self.assertRaises(ValueError):safe_input(key)

    def test_secure_selection_keys_and_redaction(self):
        for name,cls in [('grok',GrokProvider),('claude',ClaudeProvider),('kimi',KimiProvider),('deepseek',DeepSeekProvider)]:
            response=self.client.put('/api/settings',json={'ai_provider':name,'ai_model':'my-model'})
            self.assertEqual(response.status_code,200)
            key='sensitive-provider-'+name
            self.client.put('/api/secrets/ai_api_key',json={'value':key})
            self.assertIsInstance(provider(),cls)
            self.assertEqual(provider().key,key)
            self.assertNotIn(key,self.client.get('/api/settings').text)
            self.assertNotIn(key.encode(),db.DB_PATH.read_bytes())
            self.assertEqual(redact(key),'[REDACTED]')
    def test_health_and_expired_keys_no_provider_fallback(self):
        for name,cls in [('grok',GrokProvider),('claude',ClaudeProvider),('kimi',KimiProvider),('deepseek',DeepSeekProvider)]:
            prefs.save({'ai_provider':name});vault.set('ai_api_key_'+name,'test-key')
            for status in (401,402,403,429):
                with patch.object(httpx.AsyncClient,'request',AsyncMock(return_value=self.response({},status))) as request:
                    with self.assertRaises(ServiceError):asyncio.run(provider().complete('system','user'))
                    self.assertEqual(prefs.get('ai_provider'),name);request.assert_awaited_once()
            with patch.object(httpx.AsyncClient,'request',AsyncMock(return_value=self.response({'data':[{'id':'model'}]}))):
                self.assertTrue(asyncio.run(cls('model','test-key').health_check()))
