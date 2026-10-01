import asyncio
import json
from datetime import datetime,timedelta,timezone
from unittest.mock import patch,AsyncMock
from support import AppTest,db,prefs,ws,storage,x_api,vault
from app import workers,discovery,search
from app.errors import ServiceError
from app.post_urls import parse_tweet_url
from app.backup import backup_bytes,restore_bytes

class WorkflowTests(AppTest):
    def test_dashboard_onboarding_and_csrf(self):
        self.assertEqual(self.client.get("/").status_code,200)
        self.assertFalse(self.client.get("/api/bootstrap").json()["settings"]["onboarded"])
        self.assertEqual(self.post("/api/onboarding/finish").status_code,200)
        self.assertTrue(prefs.get("onboarded"))
        self.client.headers.pop("X-CSRF-Token")
        self.assertEqual(self.post("/api/drafts",{"kind":"original","text":"No"}).status_code,403)
        self.assertEqual(db.rows("SELECT * FROM drafts"),[])

    def test_url_parser_and_invalid_sources(self):
        for u in ["https://x.com/name/status/123?s=20","https://twitter.com/name/status/123/"]:
            self.assertEqual(parse_tweet_url(u)["tweet_id"],"123")
        for u in ["bad","https://x.com.evil/u/status/123","https://x.com@evil/u/status/123","javascript:alert(1)","https://[bad","https://x.com/u/status/a"]:
            with self.subTest(u=u):
                self.assertEqual(self.client.get("/parse-tweet-url",params={"tweet_url":u}).status_code,400)
        source=self.source()
        self.assertEqual(source["id"],"1234567890123456789")
        self.assertEqual(source["username"],"test_user")

    def test_approval_is_exact_and_edit_invalidates(self):
        draft=self.draft()
        with patch.object(x_api,"create_post",new_callable=AsyncMock,return_value={"data":{"id":"999"}}) as send:
            self.assertEqual(self.post(f"/api/drafts/{draft['id']}/publish").status_code,400)
            self.assertEqual(self.post(f"/api/drafts/{draft['id']}/approve").status_code,200)
            self.client.put(f"/api/drafts/{draft['id']}",json={"kind":"original","text":"Changed after approval"})
            self.assertEqual(self.post(f"/api/drafts/{draft['id']}/publish").status_code,400)
            send.assert_not_awaited()
            self.post(f"/api/drafts/{draft['id']}/approve")
            self.assertEqual(self.post(f"/api/drafts/{draft['id']}/publish").status_code,200)
            self.assertEqual(self.post(f"/api/drafts/{draft['id']}/publish").status_code,400)
            send.assert_awaited_once()
        self.assertEqual(storage.action_count_today(),1)

    def test_reply_manual_quote_and_skip(self):
        f=self.source()
        d=self.draft("reply","Specific response & a question?",f["id"])
        self.assertEqual(self.post(f"/api/drafts/{d['id']}/manual").status_code,400)
        self.post(f"/api/drafts/{d['id']}/approve")
        result=self.post(f"/api/drafts/{d['id']}/manual").json()
        from urllib.parse import urlsplit,parse_qs
        query=parse_qs(urlsplit(result["url"]).query)
        self.assertEqual(query["in_reply_to"],[f["id"]])
        self.assertEqual(query["text"],[d["text"]])
        self.assertEqual(storage.action_count_today(),0)
        self.assertEqual(db.one("SELECT status FROM activity WHERE channel='manual'")["status"],"opened")
        quote=self.draft("quote","A different useful angle.",f["id"])
        self.post(f"/api/drafts/{quote['id']}/approve")
        with patch.object(x_api,"create_quote",new_callable=AsyncMock,return_value={"data":{"id":"999"}}) as send:
            self.assertEqual(self.post(f"/api/drafts/{quote['id']}/publish").status_code,200)
            send.assert_awaited_once_with(quote["text"],f["id"])
        self.post(f"/api/drafts/{d['id']}/skip")
        self.assertEqual(ws.get_draft(d["id"])["status"],"skipped")

    def test_duplicate_similar_and_daily_hourly_limits(self):
        storage.log_action("post","This was already posted.")
        for text in ["This was already posted.","This was already posted!"]:
            d=self.draft(text=text)
            self.assertEqual(self.post(f"/api/drafts/{d['id']}/approve").status_code,400)
        prefs.save({"daily_write_cap":1})
        d=self.draft(text="Entirely unrelated useful content")
        self.assertEqual(self.post(f"/api/drafts/{d['id']}/approve").status_code,400)
        prefs.save({"daily_write_cap":100,"hourly_write_limit":1})
        self.assertEqual(self.post(f"/api/drafts/{d['id']}/approve").status_code,400)

    def test_reply_account_limit(self):
        f=self.source()
        d=self.draft("reply","What format do you prefer?",f["id"])
        prefs.save({"same_account_limit":1})
        ws.activity("reply",ws.get_draft(d["id"]),status="published",channel="API")
        self.assertEqual(self.post(f"/api/drafts/{d['id']}/approve").status_code,400)

    def test_reply_generation_ranking_skip_and_budget(self):
        f=self.source()
        with patch("app.workspace.provider") as factory:
            factory.return_value.generate_reply=AsyncMock(return_value=json.dumps({"reply":"How do you search your notes?","reason":"Specific PDF workflow question","score":87,"topic":"PDFs"}))
            d=self.post("/api/generate/reply",{"feed_id":f["id"]}).json()
            self.assertEqual(d["score"],87)
            self.assertEqual(d["status"],"draft")
            self.assertEqual(storage.action_count_today(),0)
            factory.return_value.generate_reply.return_value="SKIP"
            self.assertTrue(self.post("/api/generate/reply",{"feed_id":f["id"]}).json()["skipped"])
        self.assertEqual(db.one("SELECT ignored FROM feed_items")["ignored"],1)
        prefs.save({"daily_ai_limit":1})
        with self.assertRaises(ValueError):
            asyncio.run(ws.ai_call(lambda:AsyncMock()()))

    def test_scheduled_original_publishes_once(self):
        d=self.draft()
        self.post(f"/api/drafts/{d['id']}/approve")
        due=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
        self.assertEqual(self.post(f"/api/drafts/{d['id']}/schedule",{"due_at":due,"timezone":"Africa/Nairobi"}).status_code,200)
        db.execute("UPDATE scheduled_posts SET due_at=?",((datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat(),))
        with patch.object(x_api,"create_post",new_callable=AsyncMock,return_value={"data":{"id":"999"}}) as send:
            asyncio.run(workers.tick());asyncio.run(workers.tick())
            send.assert_awaited_once()
        self.assertEqual(db.one("SELECT status FROM scheduled_posts")["status"],"published")

    def test_scheduler_rejects_replies_and_modified_content(self):
        f=self.source();d=self.draft("reply","Useful reply",f["id"])
        self.post(f"/api/drafts/{d['id']}/approve")
        due=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
        self.assertEqual(self.post(f"/api/drafts/{d['id']}/schedule",{"due_at":due,"timezone":"UTC"}).status_code,400)
        d=self.draft();self.post(f"/api/drafts/{d['id']}/approve")
        self.post(f"/api/drafts/{d['id']}/schedule",{"due_at":due,"timezone":"UTC"})
        self.client.put(f"/api/drafts/{d['id']}",json={"kind":"original","text":"Edited scheduled text"})
        self.assertEqual(db.one("SELECT status FROM scheduled_posts")["status"],"cancelled")

    def test_recovery_marks_missed_and_uncertain_no_replay(self):
        d=self.draft();ws.approve(d["id"])
        ws.schedule(d["id"],(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),"UTC")
        db.execute("UPDATE scheduled_posts SET due_at='2000-01-01T00:00:00+00:00'")
        workers.recover()
        self.assertEqual(db.one("SELECT status FROM scheduled_posts")["status"],"missed")
        db.execute("UPDATE drafts SET status='sending'")
        workers.recover()
        self.assertEqual(ws.get_draft(d["id"])["status"],"uncertain")
        self.network.assert_not_called()

    def test_failed_reply_retains_text_and_never_retries(self):
        f=self.source();d=self.draft("reply","My final edited reply",f["id"]);ws.approve(d["id"])
        with patch.object(x_api,"create_reply",new_callable=AsyncMock,side_effect=ServiceError("X",403)) as send:
            self.assertEqual(self.post(f"/api/drafts/{d['id']}/publish").status_code,400)
            send.assert_awaited_once()
        self.assertEqual(ws.get_draft(d["id"])["text"],d["text"])
        self.assertEqual(storage.action_count_today(),0)

    def test_threads_approve_full_content_and_record_each_part(self):
        d=self.draft("thread","First useful thought.\n---\nA separate conclusion.")
        ws.approve(d["id"])
        with patch.object(x_api,"create_post",new_callable=AsyncMock,return_value={"data":{"id":"1"}}) as first,patch.object(x_api,"create_reply",new_callable=AsyncMock,return_value={"data":{"id":"2"}}) as next_post:
            result=self.post(f"/api/drafts/{d['id']}/publish")
            self.assertEqual(result.status_code,200,result.text)
            first.assert_awaited_once();next_post.assert_awaited_once_with("A separate conclusion.","1")
        self.assertEqual(storage.action_count_today(),2)

    def test_watchlist_dedup_priority_and_last_seen(self):
        data={"username":"@test_user","priority":"High","topics":"PDFs"}
        r=self.post("/api/watchlist",data);self.assertEqual(r.status_code,200)
        self.assertEqual(self.post("/api/watchlist",data).status_code,400)
        prefs.save({"read_access":True})
        payload={"data":[{"id":"99","author_id":"1","text":"A new PDF idea"}],"includes":{"users":[{"id":"1","username":"test_user"}]}}
        with patch.object(x_api,"read_endpoint",new_callable=AsyncMock,side_effect=[{"data":{"id":"1"}},payload]) as read:
            self.assertEqual(self.post(f"/api/watchlist/{r.json()['id']}/refresh").status_code,200)
            self.assertEqual(self.post(f"/api/watchlist/{r.json()['id']}/refresh").status_code,400)
            self.assertEqual(read.await_count,2)
        self.assertEqual(db.one("SELECT last_seen_id FROM watched_accounts")["last_seen_id"],"99")

    def test_topics_web_query_and_mutes(self):
        r=self.post("/api/topics",{"name":"PDF editing","keywords":"PDF editor,ebook","excluded":"spam","languages":"en"})
        self.assertEqual(r.status_code,200)
        topic=self.client.get("/api/topics").json()[0]
        self.assertIn('"PDF editor" OR "ebook"',topic["query"])
        self.assertIn('-"spam"',topic["query"])
        self.assertIn("https://x.com/search?",topic["search_url"])
        self.source()
        self.post("/api/mute/author",{"value":"test_user"})
        self.assertEqual(self.client.get("/api/feed").json(),[])

    def test_paid_search_results_metrics_and_counters(self):
        payload={"data":[{"id":"111","author_id":"1","text":"Useful PDF advice","public_metrics":{"like_count":9}}],
                 "includes":{"users":[{"id":"1","username":"test_user","name":"Test"}]}}
        with patch.object(x_api,"read_endpoint",new_callable=AsyncMock,return_value=payload) as read:
            r=self.post("/api/search",{"query":'("PDF editor" OR ebook)',"language":"en","exclude_replies":True,"author":"test_user","max_results":10})
            self.assertEqual(r.status_code,200,r.text)
            self.assertEqual(r.json()["mode"],"api")
            read.assert_awaited_once()
            self.assertEqual(read.call_args.args[0],"/tweets/search/recent")
            self.assertIn("from:test_user",read.call_args.args[1]["query"])
        status=self.client.get("/api/search/status").json()
        self.assertEqual((status["searches_today"],status["posts_retrieved_today"]),(1,1))
        self.assertEqual(status["state"],"Available")
        self.assertIn("like_count",self.client.get("/api/feed").json()[0]["metrics"])

    def test_402_fallback_same_query_and_no_repeated_retry(self):
        with patch.object(x_api,"read_endpoint",new_callable=AsyncMock,side_effect=ServiceError("X",402)) as read:
            first=self.post("/api/search",{"query":"PDF lang:en"}).json()
            second=self.post("/api/search",{"query":"PDF lang:en"}).json()
            self.assertEqual(first["mode"],"web")
            self.assertIn("Paid X API search is unavailable",first["message"])
            from urllib.parse import parse_qs,urlsplit
            self.assertEqual(parse_qs(urlsplit(first["web_url"]).query)["q"],[first["query"]])
            self.assertEqual(second["mode"],"web")
            read.assert_awaited_once()
        self.assertEqual(search.status()["state"],"Requires Credits")

    def test_web_only_and_daily_search_limit(self):
        prefs.save({"discovery_mode":"web"})
        self.assertEqual(self.post("/api/search",{"query":"PDF"}).json()["mode"],"web")
        self.assertEqual(search.status()["searches_today"],0)
        prefs.save({"discovery_mode":"automatic","daily_search_limit":1})
        with patch.object(x_api,"read_endpoint",new_callable=AsyncMock,return_value={"data":[]}) as read:
            self.post("/api/search",{"query":"PDF"})
            result=self.post("/api/search",{"query":"books"}).json()
            self.assertIn("Daily API search limit",result["message"])
            read.assert_awaited_once()

    def test_search_rate_limit_backoff(self):
        with patch.object(x_api,"read_endpoint",new_callable=AsyncMock,side_effect=ServiceError("X",429,900)) as read:
            self.post("/api/search",{"query":"PDF"})
            self.post("/api/search",{"query":"PDF"})
            read.assert_awaited_once()
        self.assertTrue(db.get_setting("read_backoff_until"))

    def test_backup_excludes_secrets_and_restore_clears_approval(self):
        vault.set("ai_api_key_gemini","unit-test-private-key")
        d=self.draft();ws.approve(d["id"])
        ws.schedule(d["id"],(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),"UTC")
        blob=backup_bytes()
        self.assertNotIn(b"unit-test-private-key",blob)
        restore_bytes(blob)
        self.assertEqual(db.rows("SELECT * FROM approved_content"),[])
        self.assertEqual(db.one("SELECT status FROM drafts")["status"],"draft")
        self.assertEqual(db.one("SELECT status FROM scheduled_posts")["status"],"cancelled")
        self.assertEqual(vault.get("ai_api_key_gemini"),"unit-test-private-key")
        with self.assertRaises(ValueError):restore_bytes(b"not sqlite")

    def test_database_migrations_idempotent(self):
        db.init_db();db.init_db()
        with db.conn() as c:
            self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0],db.SCHEMA_VERSION)
            self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='tokens'").fetchone())
