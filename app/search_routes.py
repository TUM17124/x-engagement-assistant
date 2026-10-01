from fastapi import APIRouter
from pydantic import BaseModel,Field
from . import database as db
from . import search,workspace

router=APIRouter(prefix="/api/search")
class SearchInput(BaseModel):
    query: str = Field(min_length=1,max_length=2000)
    language: str = ""
    exclude_retweets: bool = True
    exclude_replies: bool = False
    author: str = ""
    max_results: int = Field(default=20,ge=10,le=100)
class RankInput(BaseModel):
    ids: list[str] = Field(max_length=5)

@router.get("/status")
def status():
    return search.status()

@router.post("")
async def run(data: SearchInput):
    query=search.build_query(data.query,data.language,data.exclude_retweets,data.exclude_replies,data.author)
    return await search.recent_search(query,data.max_results)

@router.post("/retry-access")
def retry():
    db.set_setting("search_blocked","")
    db.set_setting("search_access","Not tested")
    return {"ok":True,"message":"The next explicit search will test access again. Existing rate-limit backoff remains."}

@router.post("/rank")
async def rank(data: RankInput):
    results=[]
    for feed_id in dict.fromkeys(data.ids):
        if not db.one("SELECT 1 FROM drafts WHERE feed_id=? AND status NOT IN ('skipped','failed')",(feed_id,)):
            results.append(await workspace.generate_reply(feed_id))
    return {"drafts":results,"message":"Results scored and drafted for review. Nothing was sent."}
