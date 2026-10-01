"""Capabilities describe implemented adapters, not promised account entitlements."""
CATALOG = {
"x": {"name":"X / Twitter","home":"https://x.com/","limit":280,"api":["read_feed","search","read_mentions","reply","publish","get_metrics"],"note":"Existing OAuth and paid X API access; free web search remains available."},
"facebook": {"name":"Facebook Pages","home":"https://www.facebook.com/","limit":63206,"api":["read_feed","read_comments","reply","comment","publish","upload_images"],"note":"Managed Pages only. Meta app review and Page permissions are required; personal-profile posting is manual.",
"authorize":"https://www.facebook.com/v25.0/dialog/oauth","token":"https://graph.facebook.com/v25.0/oauth/access_token","scopes":"pages_show_list,pages_read_engagement,pages_manage_posts,pages_manage_engagement"},
"instagram": {"name":"Instagram Professional","home":"https://www.instagram.com/","limit":2200,"api":["read_feed","read_comments","reply"],"note":"Professional accounts through Instagram Login. API replies target comments on authorized media. Local image/video publishing uses manual handoff; no public media hosting is configured.",
"authorize":"https://www.instagram.com/oauth/authorize","token":"https://api.instagram.com/oauth/access_token","scopes":"instagram_business_basic,instagram_business_manage_comments"},
"linkedin": {"name":"LinkedIn","home":"https://www.linkedin.com/feed/","limit":3000,"api":["publish"],"note":"Member text publishing requires Share on LinkedIn access. Feed/comment access is restricted; this adapter uses manual import for those features.",
"authorize":"https://www.linkedin.com/oauth/v2/authorization","token":"https://www.linkedin.com/oauth/v2/accessToken","scopes":"openid profile w_member_social"},
"tiktok": {"name":"TikTok","home":"https://www.tiktok.com/","limit":2200,"api":["read_feed"],"note":"Login Kit and Display API expose the connected creator's videos. Discovery, comments, and content publishing use manual workflows in this release.",
"authorize":"https://www.tiktok.com/v2/auth/authorize/","token":"https://open.tiktokapis.com/v2/oauth/token/","scopes":"user.info.basic,video.list","pkce":"hex"},
"youtube": {"name":"YouTube","home":"https://www.youtube.com/","limit":10000,"api":["read_comments","reply","comment"],"note":"YouTube Data API comments with authorized access and quota. Community posts and video uploads use manual Studio handoff.",
"authorize":"https://accounts.google.com/o/oauth2/v2/auth","token":"https://oauth2.googleapis.com/token","scopes":"https://www.googleapis.com/auth/youtube.force-ssl","pkce":"base64"},
"threads": {"name":"Threads","home":"https://www.threads.com/","limit":500,"api":["read_feed","read_comments","reply","publish"],"note":"Threads text publishing and replies require approved permissions. Broad discovery and local-media publishing use manual fallback.",
"authorize":"https://threads.net/oauth/authorize","token":"https://graph.threads.net/oauth/access_token","scopes":"threads_basic,threads_content_publish,threads_read_replies,threads_manage_replies"},
}

def definition(platform):
    if platform not in CATALOG:
        raise ValueError("Choose a supported social network.")
    return CATALOG[platform]

def capabilities(platform, connected=False):
    supported=set(definition(platform)["api"])
    keys=["read_feed","search","read_mentions","read_comments","reply","comment","publish","upload_images","upload_video","get_metrics"]
    values={"can_"+key:connected and key in supported for key in keys}
    values["can_schedule"]=values["can_publish"]
    values["can_manual"]=True
    return values
