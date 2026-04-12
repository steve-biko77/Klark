from fastapi import APIRouter, Header, HTTPException
from app.core.supabase import supabase
from app.services.scraper_service import scrape_source

router = APIRouter(prefix="/sources", tags=["sources"])

@router.get("/")
async def get_sources(authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    user = supabase.auth.get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Non autorise")
    user_id = user.user.id
    result = supabase.table("sources").select("*").eq("user_id", user_id).execute()
    return result.data

@router.post("/")
async def create_source(body: dict, authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    user = supabase.auth.get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Non autorise")
    user_id = user.user.id
    result = supabase.table("sources").insert({
        "user_id": user_id,
        "url": body.get("url"),
        "name": body.get("name", ""),
        "type": "rss",
        "status": "pending"
    }).execute()
    return result.data[0]

@router.post("/{source_id}/scrape")
async def scrape(source_id: str, authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    user = supabase.auth.get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Non autorise")
    source = supabase.table("sources")\
        .select("*")\
        .eq("id", source_id)\
        .single()\
        .execute()
    if not source.data:
        raise HTTPException(status_code=404, detail="Source introuvable")
    result = scrape_source(
        source_id=source_id,
        url=source.data["url"],
        user_id=user.user.id
    )
    return result