import json
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import timedelta
from zoneinfo import ZoneInfo

import anthropic
from django.conf import settings
from django.db.models import Max
from django.utils import timezone

from .ai_service import log_ai_usage, select_model
from .encryption import decrypt
from .models import Analytics, LinkedInToken, Post

_PLATFORM_INSTRUCTIONS = {
    'linkedin': 'un post LinkedIn professionnel, engageant, avec des sauts de ligne, maximum 1300 caractères',
    'twitter': 'un tweet percutant, maximum 280 caractères, sans hashtags excessifs',
    'blog': 'une introduction de blog structurée, 3 paragraphes, ton informatif',
}


def generate_post(article_title: str, article_content: str, platform: str = 'linkedin',
                   style_prompt: str = '', user_id=None, task_type: str = 'single_platform') -> str:
    instruction = _PLATFORM_INSTRUCTIONS.get(platform, _PLATFORM_INSTRUCTIONS['linkedin'])
    style = f"\nStyle de l'auteur : {style_prompt}" if style_prompt else ''

    prompt = f"""Tu es un expert en création de contenu digital.
A partir de cet article, rédige {instruction}.{style}

Titre de l'article : {article_title}

Contenu : {article_content[:2000]}

Rédige uniquement le post, sans explication ni commentaire."""

    model = select_model(task_type)
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{'role': 'user', 'content': prompt}],
    )
    log_ai_usage(
        model=model,
        tokens_in=message.usage.input_tokens,
        tokens_out=message.usage.output_tokens,
        task_type=task_type,
        user_id=user_id,
    )
    return message.content[0].text


AI_COMMAND_INSTRUCTIONS = {
    'shorten': "Réduis ce post d'environ 30% en gardant l'essentiel du message, sans perdre le sens.",
    'expand': "Développe ce post avec plus de détails et des exemples concrets, en gardant la cohérence.",
    'tone:formal': "Reformule ce post dans un ton plus professionnel et formel.",
    'tone:casual': "Reformule ce post dans un ton plus décontracté et accessible.",
    'angle:question': "Transforme le hook (première ligne) de ce post en question ouverte percutante, garde le reste du post inchangé.",
    'angle:stat': "Réécris le hook (première ligne) de ce post en l'introduisant par un chiffre ou une statistique marquante, garde le reste du post inchangé.",
    'hashtags': "Ajoute 5 hashtags pertinents à la toute fin de ce post, sans modifier le reste du texte.",
}

AI_COMMANDS = frozenset(AI_COMMAND_INSTRUCTIONS.keys())


def apply_ai_command(content: str, command: str, style_prompt: str = '', user_id=None) -> str:
    """Applique une commande /ai (shorten, expand, tone:*, angle:*, hashtags) au
    contenu d'un post existant, via Claude Haiku (routeur SCRUM-29)."""
    instruction = AI_COMMAND_INSTRUCTIONS.get(command)
    if not instruction:
        raise ValueError(f"Commande /ai inconnue : {command}")

    style = f"\nStyle de l'auteur à respecter : {style_prompt}" if style_prompt else ''
    prompt = f"""Voici un post existant :

{content}

Instruction : {instruction}{style}

Réponds uniquement avec le nouveau texte du post, sans explication ni commentaire."""

    model = select_model('inline_command')
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{'role': 'user', 'content': prompt}],
    )
    log_ai_usage(
        model=model,
        tokens_in=message.usage.input_tokens,
        tokens_out=message.usage.output_tokens,
        task_type='inline_command',
        user_id=user_id,
    )
    return message.content[0].text.strip()


# ── Analytics — collecte LinkedIn (SCRUM-36) ────────────────────────────────
#
# Déviation assumée : le prompt technique décrit une tâche Celery Beat toutes
# les 24h — non disponible (SCRUM-22, worker Celery, en cours ailleurs).
# Déclenchement manuel via POST /analytics/collect/, à rebrancher sur Celery
# Beat une fois SCRUM-22 mergé.

def _fetch_linkedin_metrics(access_token: str, post_urn: str) -> dict:
    """Appelle l'API LinkedIn pour récupérer les métriques d'un post publié.
    Lève une exception si l'appel échoue — à catcher par l'appelant pour
    dégrader gracieusement (compte non vérifié, permissions insuffisantes...)."""
    url = f'https://api.linkedin.com/v2/socialMetadata/{urllib.parse.quote(post_urn, safe="")}'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {access_token}'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def collect_post_analytics(post):
    """Collecte les métriques LinkedIn d'un post publié et les enregistre.
    Retourne None (sans lever d'exception) si le post n'a pas de post_urn, si
    l'utilisateur n'a pas de token LinkedIn, ou si l'appel API échoue — cohérent
    avec l'exigence produit \"ne pas bloquer l'affichage\" en cas d'analytics
    indisponibles."""

    if not post.post_urn:
        return None
    try:
        token = post.user.linkedin_token
    except LinkedInToken.DoesNotExist:
        return None

    try:
        data = _fetch_linkedin_metrics(decrypt(token.access_token), post.post_urn)
        likes = int(data.get('likes', 0))
        views = int(data.get('views', 0))
        shares = int(data.get('shares', 0))
        comments = int(data.get('comments', 0))
    except Exception:
        return None

    engagement_rate = round((likes + comments + shares) / views * 100, 2) if views else 0.0

    return Analytics.objects.create(
        post=post, likes=likes, views=views, shares=shares, comments=comments,
        engagement_rate=engagement_rate,
    )


def collect_analytics_for_user(user) -> int:
    """Parcourt tous les posts published avec post_urn de l'utilisateur et
    collecte leurs analytics. Retourne le nombre de posts pour lesquels la
    collecte a réussi."""

    collected = 0
    posts = Post.objects.filter(user=user, status='published').exclude(post_urn__isnull=True).exclude(post_urn='')
    for post in posts:
        if collect_post_analytics(post):
            collected += 1
    return collected


ANALYTICS_EVOLUTION_WINDOW_DAYS = 30


def get_analytics_overview(user) -> dict:
    """Vue globale (évolution engagement 30j, vues cumulées, meilleur post du
    mois, plateforme la plus efficace) + vue par post (dernière collecte de
    chaque post published, avec indicateur au-dessus/en dessous de la moyenne)."""

    since = timezone.now() - timedelta(days=ANALYTICS_EVOLUTION_WINDOW_DAYS)
    recent = list(Analytics.objects.filter(post__user=user, collected_at__gte=since).select_related('post'))

    daily = defaultdict(list)
    total_views = 0
    platform_rates = defaultdict(list)
    for a in recent:
        daily[a.collected_at.date().isoformat()].append(a.engagement_rate)
        total_views += a.views
        platform_rates[a.post.platform].append(a.engagement_rate)

    evolution = [
        {'date': day, 'engagement_rate': round(sum(rates) / len(rates), 2)}
        for day, rates in sorted(daily.items())
    ]

    best = max(recent, key=lambda a: a.engagement_rate, default=None)
    best_platform = max(
        platform_rates.items(), key=lambda kv: sum(kv[1]) / len(kv[1]), default=(None, None),
    )[0]

    all_rates = [a.engagement_rate for a in recent]
    avg_engagement = sum(all_rates) / len(all_rates) if all_rates else 0.0

    posts_data = []
    for post in Post.objects.filter(user=user, status='published').order_by('-published_at'):
        latest = post.analytics.first()
        posts_data.append({
            'post_id': post.id,
            'platform': post.platform,
            'published_at': post.published_at,
            'content_excerpt': post.content[:120],
            'analytics_available': latest is not None,
            'likes': latest.likes if latest else None,
            'views': latest.views if latest else None,
            'shares': latest.shares if latest else None,
            'comments': latest.comments if latest else None,
            'engagement_rate': latest.engagement_rate if latest else None,
            'above_average': (latest.engagement_rate > avg_engagement) if latest else None,
        })

    return {
        'evolution_30j': evolution,
        'total_views': total_views,
        'best_post': {'post_id': best.post.id, 'engagement_rate': best.engagement_rate} if best else None,
        'best_platform': best_platform,
        'average_engagement_rate': round(avg_engagement, 2),
        'posts': posts_data,
    }


# ── Streak éditorial + score d'influence (SCRUM-37) ─────────────────────────
#
# Déviation assumée : le calcul du score, décrit comme une tâche Celery Beat
# chaque lundi 8h dans le prompt technique, est recalculé à la demande (au plus
# une fois par semaine, cf. maybe_update_influence_score) — SCRUM-22 non
# disponible. Le streak, lui, est explicitement \"calculé à la demande\" par le
# ticket lui-même : aucune déviation nécessaire.

USER_TIMEZONE = ZoneInfo('Europe/Paris')


def _published_dates(user) -> set:
    return {
        timezone.localtime(dt, USER_TIMEZONE).date()
        for dt in Post.objects.filter(user=user, status='published', published_at__isnull=False)
        .values_list('published_at', flat=True)
    }


def calculate_streak(user) -> int:
    """Nombre de jours calendaires consécutifs (Europe/Paris) avec au moins un
    post published, en partant d'aujourd'hui ou d'hier. 0 si aucune publication
    ni aujourd'hui ni hier."""
    dates = _published_dates(user)
    if not dates:
        return 0

    today = timezone.localtime(timezone.now(), USER_TIMEZONE).date()
    if today not in dates and (today - timedelta(days=1)) not in dates:
        return 0

    cursor = today if today in dates else today - timedelta(days=1)
    streak = 0
    while cursor in dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def should_remind_publish_today(user) -> bool:
    """Vrai si le dernier post publié date d'hier (et rien aujourd'hui) —
    rappel discret \"publiez aujourd'hui pour maintenir votre série\"."""
    dates = _published_dates(user)
    today = timezone.localtime(timezone.now(), USER_TIMEZONE).date()
    yesterday = today - timedelta(days=1)
    return yesterday in dates and today not in dates


def update_streak(user):
    """Recalcule le streak courant depuis Post.published_at et met à jour
    streak_max si dépassé (jamais écrasé si inférieur au courant)."""
    from apps.authentication.models import Profile

    profile, _ = Profile.objects.get_or_create(user=user, defaults={'persona': 'CREATEUR', 'tone': 'EXPERT'})
    current = calculate_streak(user)
    profile.streak_current = current
    if current > profile.streak_max:
        profile.streak_max = current
    profile.save(update_fields=['streak_current', 'streak_max'])
    return profile


INFLUENCE_SCORE_MIN_INTERVAL_DAYS = 7


def calculate_influence_score(user) -> int:
    """Score 0-1000 = posts publiés 30j (30%) + engagement moyen (40%) +
    régularité du streak (30%). Pondérations exposées dans settings.py."""

    since = timezone.now() - timedelta(days=30)
    posts_count = Post.objects.filter(user=user, status='published', published_at__gte=since).count()
    posts_score = min(posts_count / 30, 1.0) * 100

    rates = list(
        Analytics.objects.filter(post__user=user, collected_at__gte=since).values_list('engagement_rate', flat=True)
    )
    avg_engagement = sum(rates) / len(rates) if rates else 0.0
    engagement_score = min(avg_engagement / 10, 1.0) * 100

    streak_score = min(calculate_streak(user) / 30, 1.0) * 100

    weighted = (
        posts_score * settings.INFLUENCE_WEIGHT_POSTS
        + engagement_score * settings.INFLUENCE_WEIGHT_ENGAGEMENT
        + streak_score * settings.INFLUENCE_WEIGHT_STREAK
    )
    return round(weighted / 100 * settings.INFLUENCE_SCORE_MAX)


def maybe_update_influence_score(user):
    """Recalcule le score d'influence si la dernière mise à jour date de plus
    de 7 jours (équivalent hebdomadaire du lundi 8h décrit dans le ticket)."""
    from apps.authentication.models import Profile

    profile, _ = Profile.objects.get_or_create(user=user, defaults={'persona': 'CREATEUR', 'tone': 'EXPERT'})
    now = timezone.now()
    if profile.influence_score_updated_at and (now - profile.influence_score_updated_at) < timedelta(days=INFLUENCE_SCORE_MIN_INTERVAL_DAYS):
        return profile

    new_score = calculate_influence_score(user)
    profile.influence_score_previous = profile.influence_score
    profile.influence_score = new_score
    profile.influence_score_updated_at = now
    profile.save(update_fields=['influence_score', 'influence_score_previous', 'influence_score_updated_at'])
    return profile


# ── Recommandations de format (SCRUM-38) ────────────────────────────────────

POST_LENGTH_BUCKETS = [('court', 0, 500), ('moyen', 500, 900), ('long', 900, float('inf'))]
POST_HOUR_BUCKETS = [('matin', 6, 11), ('midi', 11, 14), ('après-midi', 14, 18), ('soir', 18, 22)]
WEEKDAYS_FR = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']

RECOMMENDATION_MIN_POSTS_TOTAL = 5
RECOMMENDATION_CONFIDENCE_LOW = 5
RECOMMENDATION_CONFIDENCE_MEDIUM = 15


def _length_bucket(content: str) -> str:
    n = len(content)
    for label, lo, hi in POST_LENGTH_BUCKETS:
        if lo <= n < hi:
            return label
    return POST_LENGTH_BUCKETS[-1][0]


def _hour_bucket(hour: int):
    for label, lo, hi in POST_HOUR_BUCKETS:
        if lo <= hour < hi:
            return label
    return None


def _confidence(n: int) -> str:
    if n < RECOMMENDATION_CONFIDENCE_LOW:
        return 'faible'
    if n < RECOMMENDATION_CONFIDENCE_MEDIUM:
        return 'moyen'
    return 'fort'


def compute_format_recommendations(user) -> dict:
    """Analyse les posts published des 90 derniers jours par dimension
    (longueur, jour, heure, hashtags, questions) et retourne les 3 meilleures
    combinaisons par taux d'engagement moyen, avec un niveau de confiance."""

    since = timezone.now() - timedelta(days=90)
    posts = list(
        Post.objects.filter(user=user, status='published', published_at__gte=since).prefetch_related('analytics')
    )

    total_published = Post.objects.filter(user=user, status='published').count()
    if total_published < RECOMMENDATION_MIN_POSTS_TOTAL:
        return {'recommendations': [], 'message': 'Publiez plus pour obtenir des recommandations.'}

    buckets = defaultdict(list)
    for post in posts:
        latest = post.analytics.first()
        if latest is None:
            continue
        rate = latest.engagement_rate

        buckets[('longueur', _length_bucket(post.content))].append(rate)
        if post.published_at:
            local_dt = timezone.localtime(post.published_at, USER_TIMEZONE)
            buckets[('jour', WEEKDAYS_FR[local_dt.weekday()])].append(rate)
            hb = _hour_bucket(local_dt.hour)
            if hb:
                buckets[('heure', hb)].append(rate)
        buckets[('hashtags', 'avec' if '#' in post.content else 'sans')].append(rate)
        buckets[('question', 'avec' if '?' in post.content else 'sans')].append(rate)

    scored = [
        {
            'dimension': dimension, 'valeur_optimale': value,
            'engagement_moyen': round(sum(rates) / len(rates), 2), 'confiance': _confidence(len(rates)),
        }
        for (dimension, value), rates in buckets.items() if rates
    ]
    scored.sort(key=lambda r: r['engagement_moyen'], reverse=True)
    return {'recommendations': scored[:3], 'message': None}


# ── Mémoire éditoriale — style learning (SCRUM-39) ──────────────────────────
#
# Déviation assumée : tâche Celery Beat chaque dimanche 23h dans le prompt
# technique — non disponible (SCRUM-22). Déclenchement manuel via
# POST /profile/learn-style/.

STYLE_MEMORY_MIN_POSTS = 5
STYLE_MEMORY_TOP_N = 10


def _extract_style_patterns(posts_content: list[str], user_id=None) -> str:
    joined = '\n\n---\n\n'.join(posts_content)
    prompt = f"""Voici les posts LinkedIn les plus performants d'un utilisateur (les {len(posts_content)} avec le meilleur taux d'engagement) :

{joined[:6000]}

En 3 à 5 phrases courtes, décris les patterns stylistiques dominants de ces posts :
structure habituelle (type de hook, longueur, présence d'un appel à l'action),
ton émotionnel, type de vocabulaire, usage des sauts de ligne et des questions,
présence de chiffres ou d'anecdotes.

Réponds uniquement avec ces phrases, à la deuxième personne ("Vos posts..."), sans introduction ni liste à puces."""

    model = select_model('style_memory')
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(model=model, max_tokens=300, messages=[{'role': 'user', 'content': prompt}])
    log_ai_usage(
        model=model, tokens_in=message.usage.input_tokens, tokens_out=message.usage.output_tokens,
        task_type='style_memory', user_id=user_id,
    )
    return message.content[0].text.strip()


def update_style_memory(user):
    """Enrichit le style_prompt de l'utilisateur (ajout, pas remplacement) à
    partir des patterns stylistiques de ses 10 posts published les plus
    performants. Retourne None sans rien modifier si moins de 5 posts published."""
    from apps.authentication.models import Profile

    published_count = Post.objects.filter(user=user, status='published').count()
    if published_count < STYLE_MEMORY_MIN_POSTS:
        return None

    top_posts = list(
        Post.objects.filter(user=user, status='published', analytics__isnull=False)
        .annotate(best_rate=Max('analytics__engagement_rate'))
        .order_by('-best_rate')[:STYLE_MEMORY_TOP_N]
    )
    if not top_posts:
        return None

    learned_text = _extract_style_patterns([p.content for p in top_posts], user_id=user.id)

    profile, _ = Profile.objects.get_or_create(user=user, defaults={'persona': 'CREATEUR', 'tone': 'EXPERT'})
    profile.style_prompt = f"{profile.style_prompt}\n\n{learned_text}".strip()
    profile.style_history = profile.style_history + [{
        'date': timezone.now().isoformat(),
        'learned_text': learned_text,
        'posts_analyzed': len(top_posts),
    }]
    profile.save(update_fields=['style_prompt', 'style_history'])
    return profile


def reset_style_prompt(user):
    """Restaure style_prompt à la dernière valeur saisie manuellement,
    annulant l'enrichissement automatique de update_style_memory."""
    from apps.authentication.models import Profile

    profile, _ = Profile.objects.get_or_create(user=user, defaults={'persona': 'CREATEUR', 'tone': 'EXPERT'})
    profile.style_prompt = profile.style_prompt_manual
    profile.save(update_fields=['style_prompt'])
    return profile
