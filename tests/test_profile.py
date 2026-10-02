import os
from unittest.mock import patch
from fastapi.testclient import TestClient
from support import AppTest,db,prefs,main
from app.profile import ProfilePatch

class ProfileTests(AppTest):
    def test_save_all_fields_and_structured_storage(self):
        payload={key:"My "+key for key in ProfilePatch.model_fields}
        response=self.client.put("/api/profile",json=payload)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json(),payload)
        self.assertEqual(prefs.get("my_profile"),payload)
        self.assertEqual(db.rows("SELECT * FROM application_memory"),[])

    def test_partial_empty_and_optional_null(self):
        self.client.put("/api/profile",json={"name":"Ada","bio":"Builds useful tools"})
        response=self.client.put("/api/profile",json={"role":"  Founder  ","goals":"","industry":None})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()["name"],"Ada")
        self.assertEqual(response.json()["bio"],"Builds useful tools")
        self.assertEqual(response.json()["role"],"Founder")
        self.assertEqual(response.json()["industry"],"")
        self.assertEqual(self.client.put("/api/profile",json={}).status_code,200)

    def test_malformed_and_oversized_do_not_overwrite(self):
        self.client.put("/api/profile",json={"name":"Keep"})
        for payload in ({"name":17},{"role":["bad"]},{"unknown":"data"},{"bio":"x"*4001},["bad"],"bad"):
            response=self.client.put("/api/profile",json=payload)
            self.assertEqual(response.status_code,422,response.text)
            self.assertEqual(self.client.get("/api/profile").json()["name"],"Keep")

    def test_persistence_across_new_app_session(self):
        self.client.put("/api/profile",json={"name":"Ada","goals":"Thoughtful conversations"})
        db.init_db()
        with TestClient(main.app) as reopened:
            self.assertEqual(reopened.get("/api/profile").json()["goals"],"Thoughtful conversations")

    def test_legacy_profile_fields_load_then_save_canonically(self):
        prefs.save({"my_profile":{"Name":"Previous name","Bio":"Previous bio"}})
        self.assertEqual(self.client.get("/api/profile").json()["bio"],"Previous bio")
        response=self.client.put("/api/profile",json={"goals":"New goal"})
        self.assertEqual(response.json()["name"],"Previous name")
        self.assertNotIn("Name",prefs.get("my_profile"))

    def test_development_validation_logs_only_schema_metadata(self):
        secret="private-value-do-not-log"
        with patch.dict(os.environ,{"XEA_DEBUG_VALIDATION":"1"}),self.assertLogs("app.validation",level="WARNING") as logged:
            response=self.client.put("/api/profile",json={"name":{"api_key":secret},secret:"bad"})
        self.assertEqual(response.status_code,422)
        self.assertNotIn(secret," ".join(logged.output))
        self.assertNotIn(secret,response.text)
        self.assertIn("profile"," ".join(logged.output))
