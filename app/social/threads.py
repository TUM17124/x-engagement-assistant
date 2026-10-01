from .base import SocialProvider

class ThreadsProvider(SocialProvider):
    platform="threads"
    root="https://graph.threads.net/v1.0/"
    async def get_profile(self):
        p,_=await self.call("GET",self.root+"me",params={"fields":"id,username,threads_profile_picture_url"})
        return {"id":p["id"],"name":p["username"],"avatar":p.get("threads_profile_picture_url","")}
    async def get_feed(self,account_id=None):
        if account_id and account_id!=self.account.get("account_id"):self.unsupported("other creators' feeds")
        data,_=await self.call("GET",self.root+"me/threads",params={"fields":"id,text,username,permalink,timestamp","limit":20})
        return [self.item(p["id"],p.get("text",""),p.get("username",""),p.get("permalink",""),posted_at=p.get("timestamp")) for p in data.get("data",[])]
    async def get_comments(self,post_id):
        data,_=await self.call("GET",self.root+post_id+"/replies",params={"fields":"id,text,username,permalink,timestamp"})
        return [self.item(p["id"],p.get("text",""),p.get("username",""),p.get("permalink",""),content_kind="comment",posted_at=p.get("timestamp")) for p in data.get("data",[])]
    async def publish_text(self,text,target=None):
        data={"media_type":"TEXT","text":text}
        if target:data["reply_to_id"]=target
        container,_=await self.call("POST",self.root+"me/threads","write",data=data)
        post,_=await self.call("POST",self.root+"me/threads_publish","write",data={"creation_id":container["id"]})
        return post["id"]
    async def publish_post(self,text,media=None):
        if media:self.unsupported("media publishing")
        return await self.publish_text(text)
    async def publish_reply(self,target,text):return await self.publish_text(text,target)
