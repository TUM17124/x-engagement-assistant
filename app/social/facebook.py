import json
from .base import SocialProvider

class FacebookProvider(SocialProvider):
    platform="facebook"
    root="https://graph.facebook.com/v25.0/"
    async def pages(self):
        data,_=await self.call("GET",self.root+"me/accounts",params={"fields":"id,name,access_token","limit":50})
        return data.get("data",[])
    async def get_profile(self):
        data,_=await self.call("GET",self.root+"me",params={"fields":"id,name,picture"})
        return {"id":data["id"],"name":data["name"],"avatar":data.get("picture",{}).get("data",{}).get("url","")}
    async def get_feed(self,account_id=None):
        # Only the selected, authorized Page; arbitrary competitor scraping is not supported.
        page=self.account.get("account_id")
        if account_id and account_id!=page:self.unsupported("unapproved Page monitoring")
        data,_=await self.call("GET",self.root+str(page)+"/feed",params={"fields":"id,message,created_time,permalink_url,from,full_picture","limit":20})
        return [self.item(p["id"],p.get("message",""),p.get("from",{}).get("name",self.account.get("name","")),p.get("permalink_url",""),posted_at=p.get("created_time"),media=[{"url":p["full_picture"]}] if p.get("full_picture") else []) for p in data.get("data",[])]
    async def get_comments(self,post_id):
        data,_=await self.call("GET",self.root+post_id+"/comments",params={"fields":"id,message,from,created_time,permalink_url","limit":20})
        return [self.item(p["id"],p.get("message",""),p.get("from",{}).get("name",""),p.get("permalink_url",""),content_kind="comment",posted_at=p.get("created_time")) for p in data.get("data",[])]
    async def publish_reply(self,target,text):
        data,_=await self.call("POST",self.root+target+"/comments","write",data={"message":text})
        return data["id"]
    async def publish_comment(self,target,text):return await self.publish_reply(target,text)
    async def upload_media(self,media):
        from ..media import media_path
        with media_path(media["id"]).open("rb") as stream:
            data,_=await self.call("POST",self.root+self.account["account_id"]+"/photos","write",
                data={"published":"false","alt_text_custom":media.get("alt_text","")},files={"source":(media["name"],stream,media["mime"])})
        return data["id"]
    async def publish_post(self,text,media=None):
        payload={"message":text}
        if media:
            ids=[await self.upload_media(m) for m in media]
            payload["attached_media"]=json.dumps([{"media_fbid":id} for id in ids])
        data,_=await self.call("POST",self.root+self.account["account_id"]+"/feed","write",data=payload)
        return data["id"]
