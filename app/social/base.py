import json
from datetime import datetime,timedelta,timezone
import httpx
from .. import database as db, preferences as prefs
from ..secrets import store
from ..errors import check_response,ServiceError
from .catalog import definition,capabilities

class SocialProvider:
    platform=""
    def __init__(self):
        self.spec=definition(self.platform)
    @property
    def account(self):
        return db.one("SELECT * FROM social_accounts WHERE platform=?",(self.platform,)) or {}
    def config(self):
        return db.get_setting("social_config_"+self.platform,{})
    def tokens(self):
        return json.loads(store.get("social_"+self.platform+"_oauth") or "{}")
    def disconnect(self):
        store.delete("social_"+self.platform+"_oauth")
        store.delete("social_"+self.platform+"_choices")
        store.delete("social_"+self.platform+"_pending")
        db.execute("DELETE FROM social_accounts WHERE platform=?",(self.platform,))
    def connect(self):
        from .oauth import begin
        return begin(self.platform)
    def capabilities(self):
        values=capabilities(self.platform,bool(self.tokens().get("access_token")) and (self.platform=="x" or bool(self.account)))
        granted=self.tokens().get("granted_scopes","")
        requirements={
          "facebook":{"publish":"pages_manage_posts","upload_images":"pages_manage_posts","reply":"pages_manage_engagement","comment":"pages_manage_engagement","read_feed":"pages_read_engagement","read_comments":"pages_read_engagement"},
          "instagram":{"read_feed":"instagram_business_basic","read_comments":"instagram_business_manage_comments","reply":"instagram_business_manage_comments"},
          "linkedin":{"publish":"w_member_social"},"tiktok":{"read_feed":"video.list"},
          "youtube":{"read_comments":"https://www.googleapis.com/auth/youtube.force-ssl","reply":"https://www.googleapis.com/auth/youtube.force-ssl","comment":"https://www.googleapis.com/auth/youtube.force-ssl"},
          "threads":{"publish":"threads_content_publish","reply":"threads_content_publish","read_comments":"threads_read_replies"}
        }
        if granted:
            scopes=set(granted.replace(","," ").split())
            for action,scope in requirements.get(self.platform,{}).items():
                if scope not in scopes:values["can_"+action]=False
        values["can_schedule"]=values["can_publish"]
        return values
    def unsupported(self,action):
        raise ValueError(self.spec["name"]+" does not support "+action+" in this adapter. Copy your draft and open the original platform.")
    async def call(self,method,url,operation="read",**kwargs):
        if not self.tokens().get("access_token"):
            raise ValueError("Connect "+self.spec["name"]+" in Connected Accounts first.")
        state=db.get_setting("social_pause_"+self.platform,{})
        if state.get("blocked") or state.get("until","")>db.now():
            raise ValueError(state.get("message","Provider is paused. Retest access in Connected Accounts."))
        day=db.now()[:10]
        count=db.one("SELECT COUNT(*) n FROM social_usage WHERE platform=? AND substr(created_at,1,10)=?",(self.platform,day))["n"]
        if count>=prefs.get("social_daily_request_cap"):
            raise ValueError("Daily API request cap reached for "+self.spec["name"]+". Manual workflows remain available.")
        from .oauth import access_token
        request_id=db.execute("INSERT INTO social_usage(platform,operation,created_at,status) VALUES(?,?,?,'pending')",(self.platform,operation,db.now()))
        try:
            token=await access_token(self.platform)
            headers={"Authorization":"Bearer "+token,**kwargs.pop("headers",{})}
            async with httpx.AsyncClient(timeout=35) as client:
                r=await client.request(method,url,headers=headers,**kwargs)
            check_response(r,self.spec["name"])
            data=r.json() if r.content else {}
            if isinstance(data,dict) and data.get("error"):
                error=data["error"]
                code=error.get("code") if isinstance(error,dict) else None
                if code not in {None,0,"ok"}:
                    raise ServiceError(self.spec["name"],403)
            db.execute("UPDATE social_usage SET status='success' WHERE id=?",(request_id,))
            return data,r.headers
        except ServiceError as error:
            message=str(error)
            state={"message":message}
            if error.status in {401,402,403}:state["blocked"]=True
            if error.status==429:state["until"]=(datetime.now(timezone.utc)+timedelta(seconds=error.retry_after)).isoformat()
            db.set_setting("social_pause_"+self.platform,state)
            db.execute("UPDATE social_usage SET status=? WHERE id=?",(str(error.status),request_id))
            db.execute("UPDATE social_accounts SET api_status=? WHERE platform=?",(message,self.platform))
            raise
        except httpx.HTTPError:
            db.execute("UPDATE social_usage SET status='network_error' WHERE id=?",(request_id,))
            raise ValueError(self.spec["name"]+" could not be reached. Your drafts remain available.") from None
    async def get_profile(self):self.unsupported("profile retrieval")
    async def get_feed(self,**kwargs):self.unsupported("feed access")
    async def get_mentions(self):self.unsupported("mentions")
    async def get_comments(self,post_id):self.unsupported("comments")
    async def get_notifications(self):self.unsupported("notifications")
    async def get_post(self,post_id):self.unsupported("post retrieval")
    async def publish_post(self,text,media=None):self.unsupported("API publishing")
    async def publish_reply(self,target,text):self.unsupported("API replies")
    async def publish_comment(self,target,text):self.unsupported("API comments")
    async def upload_media(self,media):self.unsupported("media upload")
    async def get_metrics(self,post_id):self.unsupported("metrics")
    async def search_content(self,query):self.unsupported("API search")
    async def health_check(self):
        return await self.get_profile()
    def item(self,id,text,author="",url="",**extra):
        return {"external_id":str(id),"text":text or "", "username":author or self.account.get("name",""),
                "url":url or self.spec["home"],"platform":self.platform,"avatar":self.account.get("avatar",""),**extra}
