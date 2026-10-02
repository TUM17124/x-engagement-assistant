import asyncio,json
from unittest.mock import patch,AsyncMock
from support import AppTest,db,prefs,ws,x_api
from app import command_bus as bus
from app.command_tools import REGISTRY,Permission

class ExtendedControlTests(AppTest):
    def setUp(self):
        super().setUp();bus.CONFIRM_LOCK=asyncio.Lock();ws.WRITE_LOCK=asyncio.Lock()
    def run_plan(self,tool,**arguments):
        return asyncio.run(bus.execute_plan(bus.action(tool,**arguments),None,lambda e:None))
    def confirm(self,result):
        a=result['actions'][0]
        return asyncio.run(bus.confirm(a['id'],a['checksum']))
    def test_profile_partial_terminal_approval_preserves_other_fields(self):
        self.client.put('/api/profile',json={'name':'Ada','bio':'Keep this'})
        result=self.run_plan('profile.update',role='Founder')
        self.assertEqual(self.client.get('/api/profile').json()['role'],'')
        self.confirm(result)
        profile=self.client.get('/api/profile').json()
        self.assertEqual(profile['role'],'Founder');self.assertEqual(profile['bio'],'Keep this')
        self.assertEqual(profile['name'],'Ada')
    def test_settings_limit_requires_confirmation_and_rejects_stale(self):
        result=self.run_plan('settings.update',daily_ai_limit=100)
        self.assertEqual(prefs.get('daily_ai_limit'),50)
        prefs.save({'daily_ai_limit':60})
        with self.assertRaisesRegex(ValueError,'changed'):self.confirm(result)
        self.confirm(self.run_plan('settings.update',daily_ai_limit=100))
        self.assertEqual(prefs.get('daily_ai_limit'),100)
        for args in ({'daily_ai_limit':0},{'require_approval':False},{'ai_api_key':'never'},{'hourly_write_limit':101}):
            with self.assertRaises(ValueError):self.run_plan('settings.update',**args)
    def test_delete_draft_requires_yes_and_cancels_schedule_without_id_reuse(self):
        draft=self.draft();ws.approve(draft['id'])
        from datetime import datetime,timedelta,timezone
        ws.schedule(draft['id'],(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),'UTC')
        old=self.run_plan('content.publish',draft_id=draft['id'])['actions'][0]
        result=self.run_plan('content.deleteDraft',draft_id=draft['id'])
        self.assertEqual(ws.get_draft(draft['id'])['status'],'scheduled')
        self.confirm(result)
        self.assertEqual(db.one('SELECT status FROM action_requests WHERE id=?',(old['id'],))['status'],'cancelled')
        self.assertEqual(self.client.get('/api/social/inbox?tab=scheduled').json(),[])
        self.assertEqual(db.one('SELECT status FROM scheduled_posts')['status'],'cancelled')
        with self.assertRaises(ValueError):ws.approve(draft['id'])
        self.assertGreater(self.draft(text='Different content')['id'],draft['id'])
    def test_published_draft_cannot_be_deleted_or_reposted(self):
        draft=self.draft();db.execute("UPDATE drafts SET status='published' WHERE id=?",(draft['id'],))
        result=self.run_plan('content.deleteDraft',draft_id=draft['id'])
        with self.assertRaisesRegex(ValueError,'published'):self.confirm(result)
        value=self.run_plan('content.check',draft_id=draft['id'])['data'][0]['result']
        self.assertFalse(value['allowed']);self.network.assert_not_called()
    def test_duplicate_and_limit_feedback_without_publishing(self):
        from app.storage import log_action
        draft=self.draft();log_action('post',draft['text'])
        value=self.run_plan('content.check',draft_id=draft['id'])['data'][0]['result']
        self.assertIn('Duplicate',value['message'])
        prefs.save({'daily_write_cap':1})
        value=self.run_plan('content.check',draft_id=draft['id'])['data'][0]['result']
        self.assertIn('cap reached',value['message'])
        self.network.assert_not_called()
    def test_explicit_controls_work_without_model(self):
        commands={'show profile':'profile.read','set profile bio to Building tools':'profile.update','set profile name to Ada':'profile.update',
          'set daily ai limit to 100':'settings.update','delete draft 3':'content.deleteDraft',
          'check draft 2':'content.check','edit draft 2 to New copy':'content.edit',
          'use kimi':'settings.update','show topics':'topics.list','show limits':'system.limits'}
        for raw,tool in commands.items():
            plan=bus.parse_explicit(raw);self.assertEqual(plan.actions[0].tool,tool);bus.validate(plan)
    def test_natural_language_cannot_bypass_validation_or_confirm_itself(self):
        for tool in ('content.deleteDraft','settings.update','profile.clear','media.delete','watchlist.update'):
            self.assertIn(REGISTRY[tool].permission,{Permission.EXTERNAL_ACTION,Permission.DESTRUCTIVE})
        with self.assertRaises(ValueError):bus.validate(bus.action('approvals.confirm',id='fake'))
        with self.assertRaises(ValueError):bus.validate(bus.action('settings.update',daily_ai_limit=1000000))
        self.assertFalse(REGISTRY['settings.update'].automation_allowed)

    def test_context_media_topics_and_local_draft_schemas(self):
        created=self.run_plan('content.saveDraft',text='My own text')['data'][0]['result']
        self.assertEqual(ws.get_draft(created['id'])['status'],'draft')
        result=self.run_plan('settings.context',section='product',fields={'name':'Test product'})
        self.confirm(result);self.assertEqual(prefs.get('product')['name'],'Test product')
        result=self.run_plan('topics.create',name='AI',keywords='AI agents')
        topic=self.confirm(result)
        self.assertIsNotNone(db.one('SELECT id FROM tracked_topics WHERE id=?',(topic['id'],)))
        self.confirm(self.run_plan('topics.delete',id=topic['id']))
        self.assertIsNone(db.one('SELECT id FROM tracked_topics WHERE id=?',(topic['id'],)))
        for name,args in [('media.transform',{'id':'x','width':0,'height':3}),('content.saveDraft',{'text':'a','platform':'fake'}),('media.update',{'id':'x','path':'../escape'})]:
            with self.assertRaises(ValueError):self.run_plan(name,**args)

    def test_ai_test_uses_shared_health_and_clears_local_pause(self):
        db.set_setting('ai_pause',{'blocked':True})
        model=type('Provider',(),{'health_check':AsyncMock(return_value=True)})()
        with patch('app.providers.provider',return_value=model):self.run_plan('ai.test')
        self.assertTrue(db.get_setting('ai_health')['ok'])
        self.assertEqual(db.get_setting('ai_pause'),{})
