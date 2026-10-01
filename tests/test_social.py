import asyncio
import io
import json
import time
from datetime import datetime,timedelta,timezone
from unittest.mock import patch,AsyncMock
from urllib.parse import urlsplit,parse_qs
import httpx
from PIL import Image
from support import AppTest,db,prefs,ws,vault
from app.social import oauth,workspace as social
from app.social.registry import provider
from app.social.catalog import CATALOG
from app import media,workers
from app.errors import ServiceError

class SocialTests(AppTest):
    def connected(self,name="facebook",id="page-1"):
        vault.set("social_"+name+"_oauth",json.dumps({"access_token":"private-social-test","expires_at":time.time()+3600}))
        oauth.save_profile(name,{"id":id,"name":"Test account"})

    def test_accounts_capabilities_are_honest_and_no_password_storage(self):
        accounts=self.client.get("/api/social/accounts").json()
        self.assertEqual(len(accounts),7)
        self.assertTrue(all(not a["connected"] for a in accounts))
        self.assertTrue(all(not a["capabilities"]["can_publish"] for a in accounts))
        self.connected("tiktok")
        self.assertTrue(provider("tiktok").capabilities()["can_read_feed"])
        self.assertFalse(provider("tiktok").capabilities()["can_publish"])
        self.assertFalse(provider("instagram").capabilities()["can_publish"])
        self.assertNotIn("private-social-test",self.client.get("/api/social/accounts").text)
        self.assertNotIn(b"private-social-test",db.DB_PATH.read_bytes())

    def test_oauth_state_pkce_and_secure_pending_storage(self):
        for name in ("tiktok","youtube","linkedin","facebook","instagram","threads"):
            db.set_setting("social_config_"+name,{"client_id":"test-client","redirect_uri":"http://127.0.0.1:8787/social/auth/"+name+"/callback"})
            url=oauth.begin(name);query=parse_qs(urlsplit(url).query)
            self.assertEqual(query["response_type"],["code"])
            pending=json.loads(vault.get("social_"+name+"_pending"))
            self.assertEqual(query["state"],[pending["state"]])
            self.assertNotIn(pending["verifier"],db.DB_PATH.read_bytes().decode(errors="ignore"))
            if name=="tiktok":self.assertEqual(len(query["code_challenge"][0]),64)
            if name=="youtube":self.assertEqual(query["code_challenge_method"],["S256"])
            with self.assertRaises(ValueError):asyncio.run(oauth.finish(name,"code","wrong"))
            with self.assertRaises(ValueError):oauth.callback_values(name,"https://evil.test/callback?code=a&state=b")

    def test_oauth_exchange_profile_and_disconnect(self):
        name="linkedin"
        db.set_setting("social_config_"+name,{"client_id":"client","redirect_uri":"http://127.0.0.1:8787/social/auth/linkedin/callback"})
        oauth.begin(name);state=json.loads(vault.get("social_linkedin_pending"))["state"]
        responses=[httpx.Response(200,json={"access_token":"oauth-only-secret","expires_in":3600,"scope":"openid profile w_member_social"}),
                   httpx.Response(200,json={"sub":"person-1","name":"Mock Person"})]
        with patch.object(httpx.AsyncClient,"request",new_callable=AsyncMock,side_effect=responses):
            result=asyncio.run(oauth.finish(name,"code",state))
        self.assertTrue(result["connected"])
        self.assertEqual(provider(name).account["account_id"],"person-1")
        self.assertNotIn(b"oauth-only-secret",db.DB_PATH.read_bytes())
        provider(name).disconnect()
        self.assertFalse(provider(name).tokens())

    def test_facebook_page_selection_never_leaks_page_tokens(self):
        self.connected()
        vault.set("social_facebook_choices",json.dumps([{"id":"2","name":"Chosen Page","access_token":"private-page-token"}]))
        self.assertNotIn("private-page-token",self.client.get("/api/social/accounts").text)
        r=self.post("/api/social/accounts/facebook/select",{"id":"2"})
        self.assertEqual(r.status_code,200)
        self.assertEqual(provider("facebook").account["account_id"],"2")
        self.assertNotIn(b"private-page-token",db.DB_PATH.read_bytes())

    def test_all_manual_imports_and_platform_url_validation(self):
        for platform,url in {"facebook":"https://facebook.com/example/posts/123","instagram":"https://instagram.com/p/example/",
            "linkedin":"https://linkedin.com/feed/update/example","tiktok":"https://tiktok.com/@example/video/123",
            "youtube":"https://youtube.com/watch?v=abc","threads":"https://threads.com/@example/post/abc"}.items():
            item=social.manual_import(platform,"A useful question?",url,"Example")
            self.assertEqual(item["platform"],platform)
            self.assertEqual(item["source"],"manual")
            with self.assertRaises(ValueError):social.manual_import(platform,"text","https://evil.test/")
        self.assertEqual(len(self.client.get("/api/social/feed").json()),6)
        self.assertIsNotNone(social.manual_import("x","Text without a URL"))

    def test_cross_platform_drafts_require_exact_approval_and_account(self):
        self.connected("facebook")
        d=self.post("/api/social/drafts",{"platform":"facebook","text":"A useful Page announcement"}).json()
        self.assertEqual(self.post("/api/drafts/"+str(d["id"])+"/publish").status_code,400)
        ws.approve(d["id"])
        with patch("app.social.facebook.FacebookProvider.publish_post",new_callable=AsyncMock,return_value="page-post") as send:
            result=asyncio.run(ws.publish(d["id"]))
            self.assertTrue(result["published"]);send.assert_awaited_once()
        self.assertEqual(db.one("SELECT platform FROM activity WHERE status='published'")["platform"],"facebook")
        self.assertEqual(db.one("SELECT platform FROM actions")["platform"],"facebook")
        next_d=ws.save_draft("original","A different account-bound post",platform="facebook")
        ws.approve(next_d["id"])
        oauth.save_profile("facebook",{"id":"another-page","name":"Different page"})
        with patch("app.social.facebook.FacebookProvider.publish_post",new_callable=AsyncMock) as send:
            with self.assertRaises(ValueError):asyncio.run(ws.publish(next_d["id"]))
            send.assert_not_awaited()

    def test_manual_response_never_attempts_api_or_counts_publication(self):
        item=social.manual_import("instagram","What is a useful annotation workflow?","https://instagram.com/p/test/","test")
        draft=ws.save_draft("reply","Organize notes by question, then export a short index.",item["id"],platform="instagram")
        ws.approve(draft["id"])
        result=self.post("/api/social/drafts/"+str(draft["id"])+"/manual")
        self.assertEqual(result.status_code,200)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM actions")["n"],0)
        self.assertEqual(db.one("SELECT status FROM activity WHERE channel='manual'")["status"],"opened")

    def test_manual_schedule_is_a_reminder_and_not_a_write(self):
        d=ws.save_draft("original","An Instagram caption to post manually",platform="instagram")
        ws.approve(d["id"])
        when=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
        r=self.post("/api/social/drafts/"+str(d["id"])+"/schedule",{"due_at":when,"timezone":"Africa/Nairobi","delivery":"manual"})
        self.assertEqual(r.status_code,200,r.text)
        db.execute("UPDATE scheduled_posts SET due_at=?",((datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat(),))
        with patch("app.workers.publish",new_callable=AsyncMock) as send:
            asyncio.run(workers.tick());send.assert_not_awaited()
        self.assertEqual(db.one("SELECT status FROM scheduled_posts")["status"],"reminder")

    def test_listener_ranking_quality_and_no_auto_send(self):
        prefs.save({"interests":["PDF"],"product":{"name":"Paper Tool"}})
        item=social.manual_import("facebook","What PDF reader handles annotations well?","https://facebook.com/test","Creator")
        mock=AsyncMock(return_value='{"reply":"Great point! Keep notes next to the passage.","reason":"Specific PDF question","score":70,"topic":"PDF"}')
        with patch("app.workspace.provider") as make:
            make.return_value.generate_reply=mock
            draft=asyncio.run(social.analyze(item["id"]))
        self.assertEqual(draft["platform"],"facebook")
        self.assertEqual(draft["kind"],"comment")
        self.assertIn("Generic",draft["quality"])
        self.assertEqual(db.one("SELECT COUNT(*) n FROM actions")["n"],0)
        prefs.save({"assistant_mode":False})
        with patch("app.social.workspace.sync",new_callable=AsyncMock) as sync:
            asyncio.run(social.monitor());sync.assert_not_awaited()

    def test_trends_use_observed_local_counts_only(self):
        prefs.save({"interests":["PDF"]})
        social.manual_import("facebook","PDF notes are useful")
        social.manual_import("threads","PDF review workflow")
        result=social.trends()
        self.assertEqual(result[0]["current"],2)
        self.assertEqual(result[0]["previous"],0)
        self.assertIn("Not a platform-wide",result[0]["note"])

    def test_provider_402_and_429_pause_and_daily_cap(self):
        self.connected("youtube")
        p=provider("youtube")
        for code in (402,429):
            db.set_setting("social_pause_youtube",{})
            with patch.object(httpx.AsyncClient,"request",new_callable=AsyncMock,return_value=httpx.Response(code,headers={"Retry-After":"300"})) as request:
                with self.assertRaises(ServiceError):asyncio.run(p.get_profile())
                with self.assertRaises(ValueError):asyncio.run(p.get_profile())
                self.assertEqual(request.await_count,1)
        db.set_setting("social_pause_youtube",{})
        prefs.save({"social_daily_request_cap":1})
        with self.assertRaises(ValueError):asyncio.run(p.get_profile())

    def test_media_originals_derivatives_and_approval_binding(self):
        buffer=io.BytesIO();Image.new("RGB",(80,60),"green").save(buffer,"PNG")
        original=media.add(buffer.getvalue(),"example.png")
        copy=media.transform(original["id"],40,40)
        self.assertEqual(media.media_path(original["id"]).read_bytes(),buffer.getvalue())
        self.assertEqual(copy["parent_id"],original["id"])
        self.connected("facebook")
        draft=ws.save_draft("original","An approved image caption",platform="facebook",media_ids=[original["id"]])
        ws.approve(draft["id"])
        self.client.put("/api/media/"+original["id"],json={"alt_text":"Changed after approval"})
        with self.assertRaises(ValueError):ws.require_approved(draft["id"])
        with self.assertRaises(ValueError):media.add(b"<svg onload='bad'/>","bad.svg")
        self.assertEqual(self.client.delete("/api/media/"+original["id"]).status_code,400)

    def test_provider_payloads_and_unsupported_features(self):
        for name in ("facebook","instagram","linkedin","tiktok","youtube","threads"):self.connected(name)
        async def run():
            with patch.object(httpx.AsyncClient,"request",new_callable=AsyncMock,return_value=httpx.Response(200,json={"id":"reply-id"})) as request:
                await provider("youtube").publish_reply("parent","A thoughtful response")
                self.assertEqual(request.call_args.kwargs["json"]["snippet"]["parentId"],"parent")
                await provider("instagram").publish_reply("comment","Helpful answer")
                self.assertTrue(request.call_args.args[1].endswith("/comment/replies"))
            with patch.object(httpx.AsyncClient,"request",new_callable=AsyncMock,side_effect=[httpx.Response(200,json={"id":"container"}),httpx.Response(200,json={"id":"thread"})]) as request:
                self.assertEqual(await provider("threads").publish_post("An approved thought"),"thread")
                self.assertEqual(request.await_count,2)
            with self.assertRaises(ValueError):await provider("tiktok").publish_post("unsupported")
            with self.assertRaises(ValueError):await provider("instagram").publish_post("unsupported")
        asyncio.run(run())

    def test_ideas_export_delete_account_and_clear_local_data(self):
        self.post("/api/social/ideas",{"title":"Idea","text":"A useful explanation"})
        self.assertEqual(len(self.client.get("/api/social/ideas").json()),1)
        self.connected("facebook")
        social.manual_import("facebook","Saved local activity")
        r=self.client.delete("/api/social/accounts/facebook/data")
        self.assertEqual(r.status_code,200)
        self.assertFalse(provider("facebook").tokens())
        self.assertEqual(self.client.get("/api/social/feed?platform=facebook").json(),[])
        self.assertEqual(self.client.request("DELETE","/api/social/data",json={"confirm":"wrong"}).status_code,400)
        self.assertEqual(self.client.request("DELETE","/api/social/data",json={"confirm":"DELETE"}).status_code,200)
        self.assertEqual(self.client.get("/api/social/ideas").json(),[])

    def test_ai_billing_failure_pauses_without_repeated_requests(self):
        operation=AsyncMock(side_effect=ServiceError("AI",402))
        with self.assertRaises(ServiceError):asyncio.run(ws.ai_call(operation))
        with self.assertRaises(ValueError):asyncio.run(ws.ai_call(operation))
        self.assertEqual(operation.await_count,1)
