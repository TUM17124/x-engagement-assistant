import asyncio
from contextlib import ExitStack
from dataclasses import replace
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient
from app import drafting, main, storage, x_api
from app.post_urls import parse_tweet_url

SOURCE = {
    "tweet_url": "https://x.com/username/status/123456789?s=20",
    "tweet_text": "What makes a PDF reader useful?",
    "author_username": "username",
}


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        folder = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.stack.enter_context(patch.object(storage, "DB_PATH", Path(folder) / "test.db"))
        # Any unmocked external request is a test failure. Never use real X credentials.
        self.network = self.stack.enter_context(patch.object(
            httpx.AsyncClient, "send", side_effect=AssertionError("External network forbidden")
        ))
        self.client = self.stack.enter_context(TestClient(main.app))

    def test_dashboard_and_removed_search(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        for label in ("Draft from X Post", "Open X Search", "Generate Reply", "Publish an original post"):
            self.assertIn(label, response.text)
        self.assertIn('action="https://x.com/search" target="_blank"', response.text)
        self.assertNotIn("Search recent posts", response.text)
        self.assertEqual(self.client.post("/search", data={"query": "PDF"}).status_code, 404)
        self.assertFalse(hasattr(x_api, "recent_search"))
        self.network.assert_not_called()

    def test_url_parsing(self):
        for url in (SOURCE["tweet_url"], "https://www.x.com/username/status/123456789/",
                    "https://twitter.com/username/status/123456789#text"):
            with self.subTest(url=url):
                response = self.client.get("/parse-tweet-url", params={"tweet_url": url})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["tweet_id"], "123456789")
                self.assertEqual(response.json()["author_username"], "username")
        large = "https://x.com/user_1/status/1234567890123456789"
        self.assertEqual(parse_tweet_url(large)["tweet_id"], "1234567890123456789")

    def test_invalid_urls_are_clear_errors(self):
        for url in ("", "bad", "https://example.com/u/status/123", "https://x.com.evil.test/u/status/123",
                    "https://x.com@evil.test/u/status/123", "https://x.com/u/status/not-a-number",
                    "https://x.com/u/status/0", "javascript:alert(1)", "https://[bad",
                    "https://x.com/u/status/123/extra", "https://x.com/u/sta\ntus/123"):
            with self.subTest(url=url):
                response = self.client.get("/parse-tweet-url", params={"tweet_url": url})
                self.assertEqual(response.status_code, 400)
                self.assertIn("valid X post URL", response.json()["error"])
        with patch.object(main, "draft_reply", new_callable=AsyncMock) as ai:
            response = self.client.post("/draft", data={**SOURCE, "tweet_url": "bad"})
            self.assertEqual(response.status_code, 400)
            self.assertIn(SOURCE["tweet_text"], response.text)
            ai.assert_not_awaited()

    def test_generate_and_regenerate_never_write(self):
        with patch.object(main, "draft_reply", new_callable=AsyncMock, return_value="Useful draft") as ai:
            response = self.client.post("/draft", data={**SOURCE, "author_username": ""})
            self.assertEqual(response.status_code, 200)
            ai.assert_awaited_once_with(SOURCE["tweet_text"], "username")
            for label in ("Useful draft", "Try API Reply", "Quote Post", "Reply Manually on X", "Regenerate", "Skip"):
                self.assertIn(label, response.text)
            response = self.client.post("/draft", data={**SOURCE, "previous_draft": "My edit"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(ai.await_count, 2)
        self.assertEqual(storage.action_count_today(), 0)
        self.network.assert_not_called()

    def test_input_and_ai_errors_preserve_content(self):
        with patch.object(main, "draft_reply", new_callable=AsyncMock) as ai:
            for changes in ({"tweet_text": "   "}, {"author_username": "invalid name"}):
                self.assertEqual(self.client.post("/draft", data={**SOURCE, **changes}).status_code, 400)
            ai.assert_not_awaited()
        with patch.object(main, "draft_reply", new_callable=AsyncMock, side_effect=RuntimeError("AI unavailable")):
            response = self.client.post("/draft", data=SOURCE)
            self.assertEqual(response.status_code, 502)
            self.assertIn(SOURCE["tweet_text"], response.text)
            response = self.client.post("/draft", data={**SOURCE, "previous_draft": "Keep my edited reply"})
            self.assertIn("Keep my edited reply", response.text)
            self.assertIn("Reply Manually on X", response.text)
        error = httpx.HTTPStatusError("secret provider detail", request=httpx.Request("POST", "https://ai.test"),
                                      response=httpx.Response(429))
        with patch.object(main, "draft_reply", new_callable=AsyncMock, side_effect=error):
            response = self.client.post("/draft", data=SOURCE)
            self.assertIn("HTTP 429", response.text)
            self.assertNotIn("secret provider detail", response.text)

    def test_failed_x_write_preserves_edit_without_counting_or_retrying(self):
        for route, method in (("/reply", "create_reply"), ("/quote", "create_quote")):
            with patch.object(x_api, method, new_callable=AsyncMock, side_effect=RuntimeError("X API 403")) as send:
                response = self.client.post(route, data={**SOURCE, "tweet_id": "123456789", "text": "My edited reply"})
                self.assertEqual(response.status_code, 400)
                self.assertIn("My edited reply", response.text)
                self.assertIn("Reply Manually on X", response.text)
                send.assert_awaited_once()
        self.assertEqual(storage.action_count_today(), 0)

    def test_api_write_history_duplicates_and_daily_cap(self):
        for route, method in (("/post", "create_post"), ("/quote", "create_quote"), ("/reply", "create_reply")):
            with patch.object(x_api, method, new_callable=AsyncMock, return_value={"data": {"id": "456"}}) as send:
                data = {**SOURCE, "tweet_id": "123456789", "text": "Approved " + route}
                response = self.client.post(route, data=data, follow_redirects=False)
                self.assertEqual(response.status_code, 303)
                send.assert_awaited_once()
                self.client.post(route, data=data, follow_redirects=False)
                self.assertEqual(send.await_count, 1, "Duplicate must not reach X")
                with patch.object(main, "action_count_today", return_value=main.settings.daily_write_cap):
                    self.client.post(route, data={**data, "text": "New text"}, follow_redirects=False)
                self.assertEqual(send.await_count, 1, "Daily cap must block X write")
        self.assertEqual(storage.action_count_today(), 3)
        self.assertEqual(len(storage.recent_actions()), 3)
        self.network.assert_not_called()

    @unittest.skipUnless(shutil.which("node"), "Node required for JavaScript checks")
    def test_manual_composer_uses_edited_text_and_string_id(self):
        with patch.object(main, "draft_reply", new_callable=AsyncMock, return_value="Draft"):
            response = self.client.post("/draft", data={**SOURCE, "tweet_url": "https://x.com/user/status/1234567890123456789"})
        script = re.search(r"<script>(.*?)</script>", response.text, re.S).group(1)
        harness = r'''const vm = require('vm');
const assert = require('assert');
const code = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const elements = {
  draft: {value: 'Edited reply & question? #PDF', addEventListener() {}},
  count: {}, manual: {}
};
const context = {document: {getElementById: id => elements[id]}, URLSearchParams};
vm.createContext(context);
vm.runInContext(code, context);
const url = new URL(elements.manual.href);
assert.equal(url.origin, 'https://x.com');
assert.equal(url.pathname, '/intent/tweet');
assert.equal(url.searchParams.get('in_reply_to'), '1234567890123456789');
assert.equal(url.searchParams.get('text'), elements.draft.value);
const field = {};
assert.equal(context.copyDraft({querySelector: () => field}), true);
assert.equal(field.value, elements.draft.value);
elements.draft.value = '   ';
assert.equal(context.copyDraft({querySelector: () => field}), false);
'''
        result = subprocess.run(["node", "-e", harness], input=json.dumps(script), text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        dashboard = self.client.get("/").text
        script = re.search(r"<script>(.*?)</script>", dashboard, re.S).group(1)
        result = subprocess.run(["node", "--check"], input=script, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class AIRequestTests(unittest.TestCase):
    def test_configured_model_only_receives_source_content(self):
        config = replace(drafting.settings, ai_base_url="https://ai.test/v1", ai_api_key="test-key", ai_model="test-model")
        response = httpx.Response(200, json={"choices": [{"message": {"content": "A contextual reply"}}]},
                                  request=httpx.Request("POST", "https://ai.test/v1/chat/completions"))
        with patch.object(drafting, "settings", config), patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=response) as post:
            text = asyncio.run(drafting.draft_reply(SOURCE["tweet_text"], "username"))
            self.assertEqual(text, "A contextual reply")
            self.assertEqual(post.call_args.args[0], config.ai_base_url + "/chat/completions")
            body = post.call_args.kwargs["json"]
            self.assertEqual(body["model"], "test-model")
            self.assertEqual(body["messages"][1]["content"], "Write one reply to @username:\n\n" + SOURCE["tweet_text"])
            self.assertNotIn(SOURCE["tweet_url"], json.dumps(body))
            self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer test-key")

    def test_missing_config_and_empty_response_are_errors(self):
        with patch.object(drafting, "settings", replace(drafting.settings, ai_base_url="")):
            with self.assertRaisesRegex(RuntimeError, "Configure AI_BASE_URL"):
                asyncio.run(drafting.draft_reply("Test"))
        for payload in ({}, {"choices": [{"message": {"content": ""}}]}):
            response = httpx.Response(200, json=payload, request=httpx.Request("POST", "https://ai.test"))
            config = replace(drafting.settings, ai_base_url="https://ai.test", ai_model="test")
            with patch.object(drafting, "settings", config), patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=response):
                with self.assertRaises(RuntimeError):
                    asyncio.run(drafting.draft_reply("Test"))


if __name__ == "__main__":
    unittest.main()
