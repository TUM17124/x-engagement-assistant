import asyncio
import json
from unittest.mock import AsyncMock, patch
from support import AppTest, db, prefs, x_api, ws
from app.providers import OpenAIProvider
from app.errors import ServiceError
from app.chatgpt_auth import ChatGPTError

class PlannerFeedbackTests(AppTest):
    def test_plan_uses_interests_dates_without_reply_constraints_and_persists(self):
        prefs.save({"interests":["PDFs","Books"]})
        model=OpenAIProvider("test-model")
        with patch.object(model,"complete",AsyncMock(return_value="Seven-day plan with useful themes")) as call,patch("app.planner.provider",return_value=model):
            r=self.post("/api/social/suggest",{"task":"Weekly plan","platform":"x","timezone":"Africa/Nairobi","text":"Introduce my app"})
        self.assertEqual(r.status_code,200,r.text)
        system,raw=call.call_args.args
        self.assertNotIn("Replies should be at most",system)
        self.assertIn("Do not return SKIP",system)
        context=json.loads(raw)
        self.assertEqual(context["interests"],["PDFs","Books"])
        self.assertEqual(context["goal"],"Introduce my app")
        self.assertEqual(len(set(context["dates"])),7)
        self.assertEqual(self.client.get("/api/social/planner").json()["text"],r.json()["text"])
        self.assertEqual(db.rows("SELECT * FROM scheduled_posts"),[])
        self.assertEqual(db.rows("SELECT * FROM approved_content"),[])

    def test_failed_plan_preserves_previous_and_does_not_look_successful(self):
        db.set_setting("last_weekly_plan",{"text":"Keep this plan"})
        model=OpenAIProvider("test-model")
        with patch.object(model,"generate_plan",AsyncMock(return_value="SKIP")),patch("app.planner.provider",return_value=model):
            r=self.post("/api/social/suggest",{"task":"Weekly plan"})
        self.assertEqual(r.status_code,400)
        self.assertIn("previous plan is unchanged",r.json()["error"])
        self.assertEqual(self.client.get("/api/social/planner").json()["text"],"Keep this plan")

    def test_invalid_planner_timezone_makes_no_ai_call(self):
        with patch("app.planner.provider") as model:
            r=self.post("/api/social/suggest",{"task":"Weekly plan","timezone":"not/a-zone"})
        self.assertEqual(r.status_code,400)
        model.assert_not_called()

    def test_provider_specific_api_key_error_and_chatgpt_error(self):
        with patch("app.providers.provider") as factory:
            factory.return_value.health_check=AsyncMock(side_effect=ServiceError("OpenAI API Key",401))
            r=self.post("/api/health/ai")
        self.assertEqual(r.status_code,502)
        self.assertIn("Select ChatGPT Plan",r.json()["error"])
        self.assertEqual(r.json()["technical"],"OpenAI API Key HTTP 401")
        with patch("app.providers.provider") as factory:
            factory.return_value.health_check=AsyncMock(side_effect=ChatGPTError("Reconnect in Settings","Authorization expired",status=401))
            r=self.post("/api/health/ai")
        self.assertEqual(r.status_code,502)
        self.assertEqual(r.json()["technical"],"ChatGPT HTTP 401")

    def test_publish_failure_keeps_technical_code_and_records_no_success(self):
        d=self.draft()
        self.post('/api/drafts/'+str(d['id'])+'/approve')
        with patch.object(x_api,'create_post',AsyncMock(side_effect=ServiceError('X',402))) as send:
            r=self.post('/api/drafts/'+str(d['id'])+'/publish')
        self.assertEqual(r.status_code,502,r.text)
        self.assertEqual(r.json()['technical'],'X HTTP 402')
        self.assertIn('Copy & open manually',r.json()['error'])
        self.assertEqual(ws.get_draft(d['id'])['status'],'failed')
        self.assertEqual(db.rows('SELECT * FROM actions'),[])
        send.assert_awaited_once()
