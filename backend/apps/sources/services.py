import feedparser
from datetime import datetime, timezone
from apps.articles.models import Article
from .models import Source


def scrape_source(source: Source) -> dict:
    feed = feedparser.parse(source.url)

    if feed.bozo:
        source.status = 'error'
        source.save(update_fields=['status'])
        return {'error': 'Flux RSS invalide', 'articles_added': 0}

    articles_added = 0
    for entry in feed.entries[:10]:
        link = entry.get('link', '')
        if Article.objects.filter(source=source, url=link).exists():
            continue
        Article.objects.create(
            source=source,
            title=entry.get('title', 'Sans titre'),
            content=entry.get('summary', entry.get('description', '')),
            url=link,
            score=0.0,
            published_at=entry.get('published', None),
        )
        articles_added += 1

    source.status = 'active'
    source.last_crawled = datetime.now(timezone.utc)
    source.save(update_fields=['status', 'last_crawled'])

    return {
        'source_id': source.id,
        'articles_added': articles_added,
        'total_found': len(feed.entries),
    }
