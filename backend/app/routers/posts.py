from fastapi import APIRouter, Header, HTTPException
from app.core.supabase import supabase
from app.services.ai_service import generate_post

router = APIRouter(prefix="/posts", tags=["posts"])

@router.post("/generate")
async def generate(body: dict, authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    user = supabase.auth.get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Non autorise")

    user_id = user.user.id
    article_id = body.get("article_id")
    platform = body.get("platform", "linkedin")

    article = supabase.table("articles")\
        .select("*")\
        .eq("id", article_id)\
        .single()\
        .execute()

    if not article.data:
        raise HTTPException(status_code=404, detail="Article introuvable")

    profile = supabase.table("profiles")\
        .select("style_prompt")\
        .eq("id", user_id)\
        .execute()

    style = ""
    if profile.data and len(profile.data) > 0:
        style = profile.data[0].get("style_prompt", "") or ""

    content = generate_post(
        article_title=article.data["title"],
        article_content=article.data["content"] or "",
        platform=platform,
        style_prompt=style
    )

    result = supabase.table("posts").insert({
        "user_id": user_id,
        "article_id": article_id,
        "content": content,
        "platform": platform,
        "status": "draft"
    }).execute()

    return result.data[0]

@router.get("/")
async def get_posts(authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    user = supabase.auth.get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Non autorise")

    user_id = user.user.id
    result = supabase.table("posts")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("created_at", desc=True)\
        .execute()

    return result.data