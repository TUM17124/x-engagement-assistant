from .base import SocialProvider

class LinkedInProvider(SocialProvider):
    platform="linkedin"
    async def get_profile(self):
        p,_=await self.call("GET","https://api.linkedin.com/v2/userinfo")
        return {"id":p["sub"],"name":p.get("name",""),"avatar":p.get("picture","")}
    async def publish_post(self,text,media=None):
        if media:self.unsupported("media publishing")
        data,headers=await self.call("POST","https://api.linkedin.com/rest/posts","write",
            headers={"Linkedin-Version":"202603","X-Restli-Protocol-Version":"2.0.0"},
            json={"author":"urn:li:person:"+self.account["account_id"],"commentary":text,"visibility":"PUBLIC",
                  "distribution":{"feedDistribution":"MAIN_FEED","targetEntities":[],"thirdPartyDistributionChannels":[]},
                  "lifecycleState":"PUBLISHED","isReshareDisabledByAuthor":False})
        id=headers.get("x-restli-id") or data.get("id")
        if not id:raise RuntimeError("Publishing could not be confirmed.")
        return id
