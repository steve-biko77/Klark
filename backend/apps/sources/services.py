import calendar
from datetime import datetime, timezone

import feedparser

from apps.articles.models import Article
from apps.articles.services import detect_alerts, score_article
from apps.authentication.models import Profile
from .models import Source


def _parse_published(entry) -> datetime | None:
    """Convertit published_parsed (struct_time) en datetime UTC, ou None."""
    parsed = entry.get('published_parsed')
    if parsed:
        try:
            return datetime.utcfromtimestamp(calendar.timegm(parsed)).replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def _extract_content(entry) -> str:
    """Préfère le contenu complet (content:encoded) au résumé tronqué."""
    if entry.get('content'):
        return entry['content'][0].get('value', '')
    return entry.get('summary', entry.get('description', ''))


def _score_new_article(article: Article, profile: Profile | None) -> None:
    """Score sémantique 0-100 selon le profil ; laisse le score par défaut (0) si pas de profil
    ou si l'appel Claude échoue, pour ne jamais faire échouer le scraping à cause du scoring."""
    if profile is None:
        return
    try:
        article.score = score_article(
            article_title=article.title,
            article_content=article.content,
            persona=profile.persona,
            sector=profile.sector,
            style_prompt=profile.style_prompt,
        )
        article.save(update_fields=['score'])
    except Exception:
        pass


def _detect_new_article_alerts(article: Article, user) -> None:
    try:
        detect_alerts(article, user)
    except Exception:
        pass


def scrape_source(source: Source) -> dict:
    feed = feedparser.parse(source.url)

    if feed.bozo and not feed.entries:
        source.status = 'error'
        source.save(update_fields=['status'])
        return {'error': 'Flux RSS invalide', 'articles_added': 0}

    try:
        profile = source.user.profile
    except Profile.DoesNotExist:
        profile = None

    articles_added = 0
    for entry in feed.entries[:10]:
        link = entry.get('link', '')
        if Article.objects.filter(source=source, url=link).exists():
            continue
        article = Article.objects.create(
            source=source,
            title=entry.get('title', 'Sans titre'),
            content=_extract_content(entry),
            url=link,
            score=0.0,
            published_at=_parse_published(entry),
        )
        _score_new_article(article, profile)
        _detect_new_article_alerts(article, source.user)
        articles_added += 1

    source.status = 'active'
    source.last_crawled = datetime.now(timezone.utc)
    source.save(update_fields=['status', 'last_crawled'])

    return {
        'source_id': source.id,
        'articles_added': articles_added,
        'total_found': len(feed.entries),
    }
