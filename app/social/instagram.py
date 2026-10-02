from .base import SocialProvider

class InstagramProvider(SocialProvider):
    platform="instagram"
    root="https://graph.instagram.com/v25.0/"
    async def get_profile(self):
        data,_=await self.call("GET",self.root+"me",params={"fields":"user_id,username,name,profile_picture_url"})
        return {"id":str(data.get("user_id") or data["id"]),"name":data.get("username",""),"avatar":data.get("profile_picture_url","")}
    async def get_feed(self,account_id=None):
        if account_id and account_id!=self.account.get("account_id"):self.unsupported("other creators' feeds")
        data,_=await self.call("GET",self.root+self.account["account_id"]+"/media",params={"fields":"id,caption,permalink,timestamp,media_type,media_url,thumbnail_url","limit":20})
        return [self.item(p["id"],p.get("caption",""),url=p.get("permalink",""),posted_at=p.get("timestamp"),media=[{"url":p.get("thumbnail_url") or p["media_url"]}] if p.get("media_url") else []) for p in data.get("data",[])]
    async def get_comments(self,post_id):
        data,_=await self.call("GET",self.root+post_id+"/comments",params={"fields":"id,text,username,timestamp","limit":20})
        return [self.item(p["id"],p.get("text",""),p.get("username",""),content_kind="comment",posted_at=p.get("timestamp")) for p in data.get("data",[])]
    async def publish_reply(self,target,text):
        data,_=await self.call("POST",self.root+target+"/replies","write",data={"message":text})
        return data["id"]
