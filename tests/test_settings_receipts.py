import asyncio,json
from unittest.mock import patch,AsyncMock
from support import AppTest,db,prefs
from app import command_bus as bus
from app.context_settings import FIELDS
from app.terminal_feedback import completion_report

class SettingsReceiptTests(AppTest):
    def setUp(self):
        super().setUp();bus.CONFIRM_LOCK=asyncio.Lock()
    def request(self,tool,arguments):
        return self.post('/api/terminal/request',{'tool':tool,'arguments':arguments})
    def confirm(self,response):
        a=response.json()['actions'][0]
        return self.post('/api/terminal/approvals/'+a['id']+'/confirm',{'confirmed':True,'checksum':a['checksum']})
    def test_all_sections_approve_readback_restart_preserves_existing(self):
        prefs.save({'my_profile':{'name':'Ada'},'product':{'website':'https://example.test'}})
        patch_data={s:{k:'Useful '+k for k in fields if k not in {'name','website'}} for s,fields in FIELDS.items()}
        before=prefs.all_settings();r=self.request('settings.updateContext',patch_data)
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(prefs.all_settings(),before)
        value=self.confirm(r).json();self.assertTrue(value['verified'])
        for section,fields in patch_data.items():
            for key,text in fields.items():self.assertEqual(prefs.get(section)[key],text)
        self.assertEqual(prefs.get('product')['website'],'https://example.test')
        self.assertEqual(self.client.get('/api/profile').json()['name'],'Ada')
        db.init_db()
        self.assertEqual(self.client.get('/api/settings').json()['settings']['brand_voice']['Tone'],'Useful Tone')
        self.assertEqual(value['settings']['voice'],prefs.get('voice'))
    def test_aliases_match_gui_and_unknown_fields_rejected_before_preview(self):
        r=self.request('settings.context',{'section':'brand_voice','fields':{'tone':'Direct','humor_level':'Light'}})
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.confirm(r).status_code,200)
        self.assertEqual(prefs.get('brand_voice'),{'Tone':'Direct','Humor level':'Light'})
        count=len(db.rows('SELECT * FROM action_requests'))
        r=self.request('settings.context',{'section':'brand_voice','fields':{'invented':'No'}})
        self.assertEqual(r.status_code,400);self.assertIn('Allowed fields',r.json()['error'])
        self.assertEqual(len(db.rows('SELECT * FROM action_requests')),count)
    def test_stale_context_confirmation_rejected(self):
        r=self.request('settings.updateContext',{'voice':{'tone':'Proposed'}})
        prefs.save({'voice':{'tone':'Edited in GUI'}})
        result=self.confirm(r);self.assertEqual(result.status_code,400)
        self.assertEqual(prefs.get('voice')['tone'],'Edited in GUI')
    def test_atomic_validation_and_no_secret_fields(self):
        before=prefs.all_settings()
        for bad in [{'my_profile':{'name':'A'},'product':{'api_key':'not-allowed'}},{'voice':{'tone':123}},{'brand_voice':{}},{}]:
            self.assertEqual(self.request('settings.updateContext',bad).status_code,400)
            self.assertEqual(prefs.all_settings(),before)
        self.assertEqual(self.client.put('/api/settings',json={'voice':{'tone':'New'},'product':{'wrong':'No'}}).status_code,400)
        self.assertEqual(prefs.all_settings(),before)
    def test_no_completed_report_from_model_promise_or_claim(self):
        for text in ['I filled every setting.','I will fill it now.']:
            result=asyncio.run(bus.execute_plan(bus.Plan(message=text),None,lambda e:None))
            report=completion_report(result)
            self.assertEqual(report['state'],'attention')
            self.assertIn('No application action was executed or saved',report['message'])
        plan=bus.Plan(message='Everything is saved',actions=[bus.Action(tool='settings.updateContext',arguments={'voice':{'tone':'Direct'}})])
        result=asyncio.run(bus.execute_plan(plan,None,lambda e:None))
        self.assertNotIn('Everything is saved',result['message'])
        self.assertEqual(completion_report(result)['state'],'waiting')
        self.assertEqual(prefs.get('voice'),{})
    def test_router_sees_actual_saved_fields_and_verification_failure(self):
        prefs.save({'my_profile':{'name':'Ada'},'product':{'name':'Reader'}})
        model=type('Provider',(),{'complete':AsyncMock(return_value=json.dumps({'message':'Please review','actions':[]}))})()
        with patch('app.command_bus.provider',return_value=model):
            asyncio.run(bus.parse('Fill all my profile sections','UTC',lambda e:None))
        context=json.loads(model.complete.call_args.args[1])
        self.assertEqual(context['saved_profile_context']['my_profile']['name'],'Ada')
        self.assertIn('Humor level',context['settings_field_names']['brand_voice'])
        r=self.request('settings.updateContext',{'voice':{'tone':'Direct'}})
        with patch('app.preferences.save'):
            response=self.confirm(r)
        self.assertEqual(response.status_code,400);self.assertIn('verified',response.json()['error'])
        self.assertEqual(db.one('SELECT status FROM action_requests')['status'],'failed')
    def test_preference_empty_long_and_valid_real_text(self):
        for value in ['', '   ', 'x'*4001, {}, None]:
            r=self.request('memory.savePreference',{'key':'tone','value':value})
            self.assertEqual(r.status_code,400)
            self.assertEqual(db.rows('SELECT * FROM application_memory'),[])
        for value in ['Practical, direct and thoughtful. Avoid fake enthusiasm.', 'Useful detail. '*150]:
            r=self.request('memory.savePreference',{'key':'tone','value':value})
            self.assertEqual(r.status_code,200,r.text)
            self.assertEqual(self.client.get('/api/terminal/memory').json()[0]['value'],value.strip())

    def test_partial_failure_keeps_verified_work_in_history(self):
        plan={'message':'Will save','actions':[{'tool':'memory.savePreference','arguments':{'key':'tone','value':'Practical'}},{'tool':'ideas.update','arguments':{'id':99999,'title':'Missing','text':'No item'}}]}
        model=type('Provider',(),{'complete':AsyncMock(return_value=json.dumps(plan))})()
        with patch('app.command_bus.provider',return_value=model):
            response=self.post('/api/terminal/run',{'text':'Save my tone then edit the missing idea','timezone':'UTC'})
        self.assertIn('Completed before this failure',response.text)
        row=self.client.get('/api/terminal/history').json()[0]
        self.assertEqual(row['status'],'failed')
        result=json.loads(row['result'])
        self.assertEqual(result['data'][0]['tool'],'memory.savePreference')
        self.assertTrue(result['data'][0]['result']['verified'])
        self.assertEqual(bus.conversation_context()[-1]['tools_used'],['memory.savePreference'])
