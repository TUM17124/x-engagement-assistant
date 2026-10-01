from .base import SocialProvider

class YouTubeProvider(SocialProvider):
    platform="youtube"
    root="https://www.googleapis.com/youtube/v3/"
    async def get_profile(self):
        data,_=await self.call("GET",self.root+"channels",params={"part":"snippet","mine":"true"})
        if not data.get("items"):raise ValueError("This Google account has no accessible YouTube channel.")
        p=data["items"][0]
        return {"id":p["id"],"name":p["snippet"]["title"],"avatar":p["snippet"].get("thumbnails",{}).get("default",{}).get("url","")}
    async def get_comments(self,post_id=""):
        params={"part":"snippet","maxResults":20,"textFormat":"plainText"}
        params.update({"videoId":post_id} if post_id else {"allThreadsRelatedToChannelId":self.account["account_id"]})
        data,_=await self.call("GET",self.root+"commentThreads",params=params)
        items=[]
        for thread in data.get("items",[]):
            p=thread["snippet"]["topLevelComment"];s=p["snippet"]
            items.append(self.item(p["id"],s.get("textOriginal") or s.get("textDisplay",""),s.get("authorDisplayName",""),
                "https://www.youtube.com/watch?v="+s.get("videoId","")+"&lc="+p["id"],content_kind="comment",
                posted_at=s.get("publishedAt"),metrics={"likes":s.get("likeCount",0)}))
        return items
    async def publish_reply(self,target,text):
        data,_=await self.call("POST",self.root+"comments","write",params={"part":"snippet"},json={"snippet":{"parentId":target,"textOriginal":text}})
        return data["id"]
    async def publish_comment(self,target,text):
        data,_=await self.call("POST",self.root+"commentThreads","write",params={"part":"snippet"},
            json={"snippet":{"videoId":target,"topLevelComment":{"snippet":{"textOriginal":text}}}})
        return data["id"]
