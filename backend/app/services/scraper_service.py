import feedparser
from datetime import datetime, timezone
from app.core.supabase import supabase

def scrape_source(source_id: str, url: str, user_id: str):
    feed = feedparser.parse(url)

    if feed.bozo:
        supabase.table("sources").update({
            "status": "error"
        }).eq("id", source_id).execute()
        return {"error": "Flux RSS invalide", "articles_added": 0}

    articles_added = 0

    for entry in feed.entries[:10]:
        title = entry.get("title", "Sans titre")
        content = entry.get("summary", entry.get("description", ""))
        link = entry.get("link", "")
        published = entry.get("published", None)

        existing = supabase.table("articles")\
            .select("id")\
            .eq("source_id", source_id)\
            .eq("url", link)\
            .execute()

        if existing.data:
            continue

        supabase.table("articles").insert({
            "source_id": source_id,
            "title": title,
            "content": content,
            "url": link,
            "score": 0.0,
            "published_at": published,
        }).execute()

        articles_added += 1

    supabase.table("sources").update({
        "status": "active",
        "last_crawled": datetime.now(timezone.utc).isoformat()
    }).eq("id", source_id).execute()

    return {
        "source_id": source_id,
        "articles_added": articles_added,
        "total_found": len(feed.entries)
    }