from fastapi import APIRouter, Header, HTTPException
from app.core.supabase import supabase

router = APIRouter(prefix="/articles", tags=["articles"])

@router.get("/")
async def get_articles(authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    user = supabase.auth.get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Non autorise")

    user_id = user.user.id

    sources = supabase.table("sources")\
        .select("id")\
        .eq("user_id", user_id)\
        .execute()

    source_ids = [s["id"] for s in sources.data]

    if not source_ids:
        return []

    result = supabase.table("articles")\
        .select("*")\
        .in_("source_id", source_ids)\
        .order("created_at", desc=True)\
        .execute()

    return result.data