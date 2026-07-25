import re
from datetime import timedelta

import anthropic
from django.conf import settings
from django.utils import timezone

from apps.posts.ai_service import log_ai_usage, select_model
from .models import Alert, Article, DailyBriefing, Notification


def detect_alerts(article: Article, user) -> None:
    """Crée une Notification pour chaque alerte active dont le mot-clé apparaît
    (insensible à la casse) dans le titre ou le contenu de l'article."""
    haystack = f"{article.title} {article.content}".lower()
    for alert in Alert.objects.filter(user=user, is_active=True):
        if alert.keyword.lower() in haystack:
            Notification.objects.create(user=user, article=article, keyword=alert.keyword)


def parse_score(text: str) -> int:
    """Extrait un entier 0-100 de la réponse Claude ; 0 si rien d'exploitable."""
    match = re.search(r'\d+', text)
    if not match:
        return 0
    return max(0, min(100, int(match.group())))


def score_article(article_title: str, article_content: str, persona: str, sector: str = '', style_prompt: str = '') -> int:
    prompt = f"""Tu es un assistant qui évalue la pertinence d'un article pour un utilisateur.

Profil utilisateur :
- Persona : {persona}
- Secteur d'intérêt : {sector or 'non précisé'}
- Style éditorial : {style_prompt or 'non précisé'}

Article à évaluer :
Titre : {article_title}
Contenu : {article_content[:2000]}

Évalue la pertinence de cet article pour ce profil sur une échelle de 0 à 100.
Réponds UNIQUEMENT avec un nombre entier entre 0 et 100, sans aucune explication."""

    model = select_model('scoring')
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=model,
        max_tokens=10,
        messages=[{'role': 'user', 'content': prompt}],
    )
    log_ai_usage(
        model=model, tokens_in=message.usage.input_tokens, tokens_out=message.usage.output_tokens,
        task_type='scoring', user_id=None,
    )
    return parse_score(message.content[0].text)


BRIEFING_SCORE_THRESHOLD = 70
BRIEFING_MAX_SIGNALS = 5
BRIEFING_WINDOW_HOURS = 24


def _summarize_signal(article: Article, user_id) -> list[str]:
    prompt = f"""Tu résumes un signal de marché pour un trader pressé, en EXACTEMENT 3 lignes,
une par ligne, sans numérotation ni préfixe :
Ligne 1 : le signal clé (ce qui s'est passé)
Ligne 2 : la source et sa fiabilité
Ligne 3 : l'implication marché potentielle

Titre : {article.title}
Contenu : {article.content[:1500]}
Source : {article.source.name or article.source.url}

Réponds uniquement avec les 3 lignes, rien d'autre."""

    model = select_model('flash_briefing')
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=model,
        max_tokens=200,
        messages=[{'role': 'user', 'content': prompt}],
    )
    log_ai_usage(
        model=model, tokens_in=message.usage.input_tokens, tokens_out=message.usage.output_tokens,
        task_type='flash_briefing', user_id=user_id,
    )
    lines = [line.strip() for line in message.content[0].text.strip().split('\n') if line.strip()]
    return lines[:3]


def generate_daily_briefing(user) -> DailyBriefing:
    """Génère (ou retourne) le briefing flash du jour : jusqu'à 5 articles score > 70
    des dernières 24h, résumés en 3 lignes chacun. Idempotent — un seul briefing par
    utilisateur et par jour."""
    today = timezone.now().date()
    existing = DailyBriefing.objects.filter(user=user, date=today).first()
    if existing:
        return existing

    since = timezone.now() - timedelta(hours=BRIEFING_WINDOW_HOURS)
    articles = Article.objects.filter(
        source__user=user, score__gt=BRIEFING_SCORE_THRESHOLD, created_at__gte=since,
    ).order_by('-score')[:BRIEFING_MAX_SIGNALS]

    content = [
        {
            'article_id': article.id,
            'article_title': article.title,
            'lines': _summarize_signal(article, user.id),
        }
        for article in articles
    ]

    return DailyBriefing.objects.create(user=user, date=today, content=content)
