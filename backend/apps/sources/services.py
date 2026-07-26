import calendar
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

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


# ── Détection automatique de flux RSS (SCRUM-24) ────────────────────────────

_FEED_LINK_TYPES = {'application/rss+xml', 'application/atom+xml'}
_CANDIDATE_PATHS = ['/feed', '/rss', '/feed.xml', '/rss.xml', '/atom.xml']
_DETECTION_TIMEOUT_SECONDS = 5


class _FeedLinkParser(HTMLParser):
    """Cherche les balises <link rel="alternate" type="application/rss+xml|atom+xml">
    dans le <head> d'une page HTML."""

    def __init__(self):
        super().__init__()
        self.feed_links = []

    def handle_starttag(self, tag, attrs):
        if tag != 'link':
            return
        attrs_dict = dict(attrs)
        if attrs_dict.get('rel') == 'alternate' and attrs_dict.get('type') in _FEED_LINK_TYPES:
            href = attrs_dict.get('href')
            if href:
                self.feed_links.append(href)


def _fetch_html(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Klark/1.0'})
        with urllib.request.urlopen(req, timeout=_DETECTION_TIMEOUT_SECONDS) as resp:
            return resp.read().decode(errors='ignore')
    except Exception:
        return None


def _is_valid_feed(url: str) -> bool:
    return bool(feedparser.parse(url).entries)


def detect_feed_urls(url: str) -> list[str]:
    """Détecte le(s) flux RSS/Atom associé(s) à une URL (SCRUM-24) :
    1. L'URL est peut-être déjà un flux valide.
    2. Sinon, cherche les balises <link rel="alternate" type="application/rss+xml|atom+xml">
       dans le HTML de la page.
    3. Sinon, essaie des chemins conventionnels (/feed, /rss, /feed.xml...).
    Retourne la liste des flux trouvés (vide si aucun détecté ou URL inaccessible)."""
    if _is_valid_feed(url):
        return [url]

    html = _fetch_html(url)
    if html is None:
        return []

    parser = _FeedLinkParser()
    parser.feed(html)
    if parser.feed_links:
        return [urllib.parse.urljoin(url, href) for href in parser.feed_links]

    parsed = urllib.parse.urlparse(url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    return [
        root + path for path in _CANDIDATE_PATHS
        if _is_valid_feed(root + path)
    ]


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
