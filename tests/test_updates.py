from contextlib import closing
import asyncio
import json
import os
from unittest.mock import patch, AsyncMock
import httpx
from support import AppTest, db, prefs
from app import updates

def release(version="9.0.0"):
    base=updates.GITHUB+"/releases/download/v"+version+"/"
    return {"tag_name":"v"+version,"html_url":updates.GITHUB+"/releases/tag/v"+version,
            "body":"A real release note.","assets":[{"name":name,"browser_download_url":base+name}
            for name in (updates.ASSET,updates.UPDATE_ASSET+".sig","latest.json")]}

class UpdateTests(AppTest):
    def response(self,status,data=None,headers=None):
        return httpx.Response(status,json=data,headers=headers,request=httpx.Request("GET",updates.RELEASE_API))

    def test_check_cache_and_etag(self):
        self.network.side_effect=None
        self.network.return_value=self.response(200,release(),{"etag":"version-one"})
        first=self.post("/api/updates/check").json()
        self.assertTrue(first["release"]["available"])
        self.assertTrue(first["release"]["signed"])
        self.post("/api/updates/check")
        self.assertEqual(self.network.call_count,1)
        saved=db.get_setting("release_status");saved["attempted_at"]=0;db.set_setting("release_status",saved)
        self.network.return_value=self.response(304)
        self.post("/api/updates/check")
        self.assertEqual(self.network.call_args.args[0].headers["if-none-match"],"version-one")

    def test_unpublished_offline_and_rate_limit(self):
        self.network.side_effect=None
        self.network.return_value=self.response(404)
        self.assertIn("No public",self.post("/api/updates/check").json()["release"]["message"])
        db.set_setting("release_status",{})
        self.network.return_value=self.response(429,headers={"retry-after":"7200"})
        data=self.post("/api/updates/check").json()
        self.assertIn("limited",data["release"]["error"])
        self.post("/api/updates/check")
        self.assertEqual(self.network.call_count,2)
        db.set_setting("release_status",{})
        self.network.side_effect=httpx.ConnectError("offline")
        self.assertIn("internet",self.post("/api/updates/check").json()["release"]["error"])

    def test_untrusted_releases_rejected(self):
        for value in ("9.0.0-beta","9.0","junk"):
            with self.assertRaises(ValueError):updates.version_tuple(value)
        for change in ("url","asset","prerelease"):
            data=release()
            if change=="url":data["html_url"]="https://example.com"
            if change=="asset":data["assets"][0]["browser_download_url"]="https://example.com/evil.exe"
            if change=="prerelease":data["prerelease"]=True
            with self.assertRaises(ValueError):updates.parse_release(data)

    def test_install_requires_exact_confirmation_and_desktop(self):
        db.set_setting("release_status",updates.parse_release(release()))
        self.assertEqual(self.post("/api/updates/install",{"version":"9.0.0","confirmed":True}).status_code,400)
        with patch.dict(os.environ,{"XEA_DESKTOP_TOKEN":"test-owner"}):
            for body in ({"version":"9.0.0"},{"version":"8.0.0","confirmed":True}):
                self.assertEqual(self.post("/api/updates/install",body).status_code,400)
            self.assertEqual(self.post("/api/updates/install",{"version":"9.0.0","confirmed":True,"url":"https://evil.test"}).status_code,422)
            good=self.post("/api/updates/install",{"version":"9.0.0","confirmed":True})
            self.assertEqual(good.status_code,200,good.text)
            self.assertEqual(self.post("/api/updates/install",{"version":"9.0.0","confirmed":True}).status_code,400)
            self.assertEqual(self.client.get("/desktop/update-request").status_code,403)
            headers={"X-Desktop-Token":"test-owner"}
            self.assertEqual(self.client.get("/desktop/update-request",headers=headers).json()["state"],"downloading")
            self.assertEqual(self.client.get("/desktop/update-request",headers=headers).json(),{})

    def test_progress_is_private_and_cannot_replace_release(self):
        db.set_setting("update_installation",{"id":"one","version":"9.0.0","state":"downloading"})
        body={"id":"one","state":"installing","message":"Verified"}
        self.assertEqual(self.post("/desktop/update-progress",body).status_code,403)
        with patch.dict(os.environ,{"XEA_DESKTOP_TOKEN":"owner"}):
            response=self.client.post("/desktop/update-progress",json=body,headers={"X-Desktop-Token":"owner"})
            self.assertEqual(response.status_code,200)
            body["state"]="downloading"
            self.client.post("/desktop/update-progress",json=body,headers={"X-Desktop-Token":"owner"})
            self.assertEqual(db.get_setting("update_installation")["state"],"installing")

    def test_recovery_never_replays_install(self):
        db.set_setting("update_installation",{"version":"9.0.0","state":"installing"})
        updates.recover_updates()
        self.assertEqual(db.get_setting("update_installation")["state"],"interrupted")
        db.set_setting("update_installation",{"version":updates.VERSION,"state":"installing"})
        updates.recover_updates()
        self.assertEqual(db.get_setting("update_installation")["state"],"completed")

    def test_free_email_has_no_credentials_or_address_collection(self):
        from urllib.parse import parse_qs,urlsplit
        data=self.client.get("/api/updates").json()
        url=urlsplit(data["email_signup_url"])
        self.assertEqual(url.hostname,"blogtrottr.com")
        self.assertEqual(parse_qs(url.query)["subscribe"],[updates.GITHUB+"/releases.atom"])
        self.assertNotIn("email",data["settings"])
        self.network.assert_not_called()

    def test_install_blocks_active_publishing_and_unsigned_release(self):
        db.set_setting("release_status",updates.parse_release(release()))
        with patch.dict(os.environ,{"XEA_DESKTOP_TOKEN":"owner"}), patch.object(updates,"busy",return_value=True):
            self.assertIn("finish",self.post("/api/updates/install",{"version":"9.0.0","confirmed":True}).json()["error"])
        data=release();data["assets"]=data["assets"][:1]
        db.set_setting("release_status",updates.parse_release(data))
        with patch.dict(os.environ,{"XEA_DESKTOP_TOKEN":"owner"}):
            self.assertEqual(self.post("/api/updates/install",{"version":"9.0.0","confirmed":True}).status_code,400)

    def test_update_prepares_readable_backup_before_shutdown(self):
        import sqlite3
        from unittest.mock import Mock
        self.draft(text="Keep this local draft across updates.")
        db.set_setting("update_installation",{"id":"one","version":"9.0.0","state":"installing"})
        stop=Mock()
        with patch.dict(os.environ,{"XEA_DESKTOP_TOKEN":"owner"}), patch("app.paths.data_dir",return_value=db.DB_PATH.parent), patch("app.desktop_control.shutdown_handler",stop):
            response=self.client.post("/desktop/prepare-update",headers={"X-Desktop-Token":"owner"})
        self.assertEqual(response.status_code,200,response.text)
        stop.assert_called_once()
        with closing(sqlite3.connect(db.DB_PATH.parent/"backups"/("before-update-"+updates.VERSION+".sqlite3"))) as backup:
            self.assertEqual(backup.execute("SELECT text FROM drafts").fetchone()[0],"Keep this local draft across updates.")

    def test_installed_version_does_not_keep_stale_update_badge(self):
        db.set_setting("release_status",{"version":updates.VERSION,"available":True})
        self.assertFalse(self.client.get("/api/updates").json()["release"]["available"])

    def test_release_message_distinguishes_local_build_and_published_release(self):
        with patch.object(updates,"VERSION","0.3.2"):
            self.assertIn("Unpublished local changes",updates.release_message({"version":"0.3.2","checked_at":"today"}))
            self.assertIn("newer than",updates.release_message({"version":"0.3.1","checked_at":"today"}))
            self.assertIn("is available",updates.release_message({"version":"0.3.3","checked_at":"today"}))
            self.assertIn("No successful",updates.release_message({"version":"0.3.2"}))
            self.assertEqual(updates.release_message({"error":"Offline"}),"Offline")

    def test_update_api_explains_unpublished_local_changes(self):
        db.set_setting("release_status",{"version":updates.VERSION,"checked_at":"today"})
        response=self.client.get("/api/updates").json()
        self.assertIn("Unpublished local changes",response["release_message"])

    def test_download_links_exist_only_for_official_published_assets(self):
        data=release();parsed=updates.parse_release(data)
        downloads={d["id"]:d for d in parsed["downloads"]}
        self.assertTrue(downloads["windows-x64"]["available"])
        self.assertIsNone(downloads["macos-arm64"]["url"])
        base=updates.GITHUB+"/releases/download/v9.0.0/"
        assets={filename:base+filename for _,_,filename in updates.PLATFORM_INSTALLERS}
        self.assertTrue(all(d["available"] for d in updates.installer_downloads(assets,base)))
        assets["Social-Engagement-Command-Center-arm64.dmg"]="https://evil.test/app.dmg"
        downloads={d["id"]:d for d in updates.installer_downloads(assets,base)}
        self.assertFalse(downloads["macos-arm64"]["available"])

    def test_legacy_cache_refetches_missing_download_catalog(self):
        db.set_setting("release_status",{"version":"9.0.0","etag":"old-cache","attempted_at":0})
        self.network.side_effect=None
        self.network.return_value=self.response(200,release(),{"etag":"updated-cache"})
        result=self.post("/api/updates/check").json()
        self.assertNotIn("if-none-match",self.network.call_args.args[0].headers)
        self.assertTrue(result["release"]["downloads"])
