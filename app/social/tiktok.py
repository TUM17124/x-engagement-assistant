from .base import SocialProvider

class TikTokProvider(SocialProvider):
    platform="tiktok"
    async def get_profile(self):
        data,_=await self.call("GET","https://open.tiktokapis.com/v2/user/info/",params={"fields":"open_id,display_name,avatar_url"})
        p=data["data"]["user"]
        return {"id":p["open_id"],"name":p["display_name"],"avatar":p.get("avatar_url","")}
    async def get_feed(self,account_id=None):
        if account_id and account_id!=self.account.get("account_id"):self.unsupported("other creators' feeds")
        data,_=await self.call("POST","https://open.tiktokapis.com/v2/video/list/",params={"fields":"id,title,video_description,create_time,share_url,like_count,comment_count"},json={"max_count":20})
        from datetime import datetime,timezone
        return [self.item(p["id"],p.get("video_description") or p.get("title",""),url=p.get("share_url",""),
            posted_at=datetime.fromtimestamp(p["create_time"],timezone.utc).isoformat() if p.get("create_time") else None,
            metrics={k:p[k] for k in ("like_count","comment_count") if k in p}) for p in data.get("data",{}).get("videos",[])]
