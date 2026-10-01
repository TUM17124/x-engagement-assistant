from .base import SocialProvider
from .. import x_api,search,discovery,database as db
from ..storage import load_tokens,clear_tokens

class XProvider(SocialProvider):
    platform="x"
    def tokens(self):return load_tokens() or {}
    def disconnect(self):clear_tokens();db.set_setting("x_profile",None)
    async def get_profile(self):
        p=await x_api.me()
        return {"id":p["id"],"name":p["username"],"avatar":p.get("profile_image_url","")}
    async def get_feed(self,account_id=None):
        p=await self.get_profile()
        if account_id and not account_id.isdigit():
            user=await discovery.read("/users/by/username/"+account_id.lstrip("@"))
            account_id=user["data"]["id"]
        payload=await discovery.read("/users/"+(account_id or p["id"])+"/tweets",{**discovery.FIELDS,"max_results":10})
        return self.normalize(payload)
    def normalize(self,payload):
        users={u["id"]:u for u in payload.get("includes",{}).get("users",[])}
        return [self.item(p["id"],p["text"],users.get(p.get("author_id"),{}).get("username","unknown"),
            "https://x.com/i/web/status/"+p["id"],metrics=p.get("public_metrics",{}),posted_at=p.get("created_at")) for p in payload.get("data",[])]
    async def get_mentions(self):
        p=await self.get_profile()
        return [dict(x,content_kind="mention") for x in self.normalize(await discovery.read("/users/"+p["id"]+"/mentions",{**discovery.FIELDS,"max_results":10}))]
    async def get_post(self,id):return await discovery.fetch_post(id)
    async def publish_post(self,text,media=None):
        if media:self.unsupported("media publishing")
        return (await x_api.create_post(text))["data"]["id"]
    async def publish_reply(self,target,text):return (await x_api.create_reply(text,target))["data"]["id"]
    async def get_metrics(self,id):return await x_api.read_endpoint("/tweets/"+id,{"tweet.fields":"public_metrics"})
    async def search_content(self,query):return await search.recent_search(query)
