import asyncio,json,time
from unittest.mock import patch,AsyncMock
import httpx
from support import AppTest,db,vault
from app import video_providers as video
class VideoTests(AppTest):
    def configure(self,kind='grok'):
        vault.set('video_api_key_'+kind,'private-video-key');db.set_setting('video_configuration',{'provider':kind,'model':'video-model','daily_limit':3})
    def test_setup_listing_secure_key_and_no_generation(self):
        for kind,cls in video.ADAPTERS.items():
            with patch.object(cls,'models',AsyncMock(return_value=[{'id':'video-model','name':'Video'}])),patch.object(cls,'start',AsyncMock()) as start:
                body={'provider':kind,'model':'video-model','api_key':'private-video-key'}
                r=self.client.put('/api/video/settings',json=body);self.assertEqual(r.status_code,200,r.text)
                self.assertNotIn('private-video-key',self.client.get('/api/video/settings').text)
                self.assertNotIn('private-video-key',db.DB_PATH.read_bytes().decode(errors='ignore'));start.assert_not_called()
                self.assertEqual(self.client.delete('/api/video/keys/'+kind).status_code,200)
    def test_exact_confirmation_idempotency_restart_and_local_only(self):
        self.configure();body={'prompt':'A quiet forest','request_id':'test-request-id-123456','confirmed':False}
        self.assertEqual(self.post('/api/video/jobs',body).status_code,400)
        body['confirmed']=True
        with patch.object(video.XAIVideoProvider,'start',AsyncMock(return_value='remote-123')) as start:
            r=self.post('/api/video/jobs',body);self.assertEqual(r.status_code,200,r.text)
            db.init_db();self.post('/api/video/jobs',body);start.assert_awaited_once()
        self.assertEqual(self.client.get('/api/video/jobs').json()[0]['status'],'processing')
        db.set_setting('ai_policy',{'local_only':True});body['request_id']='other-request-id-12345'
        self.assertEqual(self.post('/api/video/jobs',body).status_code,400)
        self.assertEqual(db.rows('SELECT * FROM drafts'),[])
    def test_native_protocols_and_errors(self):
        for kind,cls in video.ADAPTERS.items():
            obj=cls('secret');models={'models':[{'id':'model'}]} if kind=='grok' else {'models':[{'name':'models/model','supportedGenerationMethods':['predictLongRunning']}]}
            with patch.object(obj,'call',AsyncMock(return_value=models)):self.assertEqual(asyncio.run(obj.models())[0]['id'],'model')
            result={'request_id':'remote'} if kind=='grok' else {'name':'models/model/operations/remote'}
            with patch.object(obj,'call',AsyncMock(return_value=result)) as call:
                asyncio.run(obj.start('model','Forest'));self.assertIn('Forest',json.dumps(call.call_args.kwargs))
            with patch.object(obj,'call',AsyncMock(return_value={'status':'failed'} if kind=='grok' else {'error':{'code':400}})):
                self.assertEqual(asyncio.run(obj.status('remote' if kind=='grok' else 'operations/remote'))[0],'failed')
    def test_poll_output_kept_in_vault_download_and_no_auth_forward(self):
        self.configure();ident='test-video-id-1234567'
        db.execute("INSERT INTO video_jobs(id,provider,model,prompt,fingerprint,remote_id,status,created_at) VALUES(?,?,?,?,?,?,?,?)",(ident,'grok','model','Forest','hash','remote','processing',db.now()))
        with patch.object(video.XAIVideoProvider,'status',AsyncMock(return_value=('ready','https://vidgen.x.ai/video.mp4?signature=private'))):
            r=self.post('/api/video/jobs/'+ident+'/status');self.assertEqual(r.json()['status'],'ready');self.assertNotIn('signature',r.text)
        self.assertNotIn('signature=private',db.DB_PATH.read_bytes().decode(errors='ignore'))
        response=httpx.Response(200,content=b'\x00\x00\x00\x18ftypisom'+b'0'*20,request=httpx.Request('GET','https://vidgen.x.ai/video.mp4'))
        with patch.object(httpx.AsyncClient,'send',AsyncMock(return_value=response)) as send:
            r=self.post('/api/video/jobs/'+ident+'/save');self.assertEqual(r.status_code,200,r.text)
            self.assertNotIn('authorization',send.call_args.kwargs['request'].headers)
        self.assertEqual(db.one('SELECT mime FROM media')['mime'],'video/mp4')
        self.assertEqual(self.client.get('/api/video/jobs').json()[0]['status'],'saved')
    def test_unknown_submission_never_retries_and_invalid_host(self):
        self.configure();body={'prompt':'A forest scene','request_id':'test-request-id-99999','confirmed':True}
        with patch.object(video.XAIVideoProvider,'start',AsyncMock(side_effect=ValueError('No ID'))) as start:
            self.assertEqual(self.post('/api/video/jobs',body).status_code,400);self.post('/api/video/jobs',body);start.assert_awaited_once()
        self.assertEqual(self.client.get('/api/video/jobs').json()[0]['status'],'uncertain')
        for url in ('http://vidgen.x.ai/a','https://evil.test/a','https://vidgen.x.ai@evil.test/a','https://vidgen.x.ai:99/a'):
            with self.assertRaises(ValueError):video.validate_download(url,'grok')
