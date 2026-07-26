import re
from datetime import datetime, timedelta

import anthropic
import fitz
from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.html import strip_tags

from apps.authentication.models import Profile
from apps.posts.ai_service import log_ai_usage, select_model
from .models import Alert, Article, DailyBriefing, Notification


def extract_pdf_text(file) -> str:
    """Extrait le texte d'un PDF page par page. Lève une exception si le
    fichier n'est pas un PDF exploitable."""
    data = file.read()
    doc = fitz.open(stream=data, filetype='pdf')
    try:
        return ''.join(page.get_text() for page in doc)
    finally:
        doc.close()


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


UNSUBSCRIBE_TOKEN_SALT = 'klark-digest-unsubscribe'
UNSUBSCRIBE_TOKEN_MAX_AGE = 60 * 60 * 24 * 30  # 30 jours


def make_unsubscribe_token(user_id: int) -> str:
    return signing.dumps({'user_id': user_id}, salt=UNSUBSCRIBE_TOKEN_SALT)


def verify_unsubscribe_token(token: str) -> int | None:
    try:
        data = signing.loads(token, salt=UNSUBSCRIBE_TOKEN_SALT, max_age=UNSUBSCRIBE_TOKEN_MAX_AGE)
        return data['user_id']
    except signing.BadSignature:
        return None


def build_digest_email_html(signals: list[dict], unsubscribe_url: str) -> str:
    if not signals:
        signals_html = '<p style="color:#6b7280;">Peu d\'actualités pertinentes aujourd\'hui.</p>'
    else:
        cards = []
        for s in signals:
            lines_html = ''.join(
                f'<p style="margin:0 0 4px;color:#4b5563;font-size:14px;">{line}</p>'
                for line in s['lines']
            )
            post_url = f"{settings.FRONTEND_URL}/posts/new?article_id={s['article_id']}"
            cards.append(f'''
                <div style="background:#f9fafb;border-radius:8px;padding:16px;margin-bottom:12px;">
                  <p style="font-weight:600;margin:0 0 8px;color:#111827;">{s['article_title']}</p>
                  {lines_html}
                  <a href="{post_url}" style="display:inline-block;margin-top:8px;color:#4f46e5;font-size:13px;text-decoration:none;">Générer un post →</a>
                </div>
            ''')
        signals_html = ''.join(cards)

    return f'''
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:#4f46e5;padding:24px;text-align:center;">
        <h1 style="color:white;margin:0;font-size:20px;">⚡ Klark — Briefing du jour</h1>
      </div>
      <div style="padding:24px;background:white;">
        {signals_html}
      </div>
      <div style="padding:16px 24px;text-align:center;font-size:12px;color:#9ca3af;">
        <a href="{unsubscribe_url}" style="color:#9ca3af;">Se désabonner du digest email</a>
      </div>
    </div>
    '''


def maybe_send_daily_digest(user) -> bool:
    """Envoie le digest email du jour si l'utilisateur a activé email_digest sur
    son profil. Réutilise le briefing déjà généré aujourd'hui s'il existe (même
    contenu que le briefing flash dashboard, cf. generate_daily_briefing).
    Retourne True si un email a effectivement été envoyé."""
    try:
        profile = user.profile
    except Profile.DoesNotExist:
        return False

    if not profile.email_digest:
        return False

    briefing = generate_daily_briefing(user)
    signals = briefing.content
    count = len(signals)
    subject = (
        f"Klark — {count} signal{'aux' if count > 1 else ''} marché d'aujourd'hui"
        if count else "Klark — votre briefing du jour"
    )
    unsubscribe_url = f"{settings.FRONTEND_URL}/unsubscribe?token={make_unsubscribe_token(user.id)}"
    html_message = build_digest_email_html(signals, unsubscribe_url)

    send_mail(
        subject=subject,
        message=strip_tags(html_message),
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
    return True


# ── Digest hebdomadaire (SCRUM-40) ───────────────────────────────────────────
#
# Réutilise l'architecture email du digest matinal (SCRUM-32). Déviation
# assumée : tâche Celery Beat chaque lundi 8h dans le prompt technique — non
# disponible (SCRUM-22). Déclenchement manuel via POST /briefings/send-weekly-digest/.

WEEKLY_UNSUBSCRIBE_TOKEN_SALT = 'klark-weekly-digest-unsubscribe'


def make_weekly_unsubscribe_token(user_id: int) -> str:
    return signing.dumps({'user_id': user_id}, salt=WEEKLY_UNSUBSCRIBE_TOKEN_SALT)


def verify_weekly_unsubscribe_token(token: str) -> int | None:
    try:
        data = signing.loads(token, salt=WEEKLY_UNSUBSCRIBE_TOKEN_SALT, max_age=UNSUBSCRIBE_TOKEN_MAX_AGE)
        return data['user_id']
    except signing.BadSignature:
        return None


def gather_weekly_stats(user) -> dict:
    """Statistiques de la semaine écoulée (lundi-dimanche précédent, Europe/Paris) :
    posts générés/publiés, engagement moyen, streak, score d'influence + tendance,
    meilleur post de la semaine."""
    from apps.posts.models import Analytics, Post
    from apps.posts.services import USER_TIMEZONE

    now_local = timezone.localtime(timezone.now(), USER_TIMEZONE)
    this_monday = now_local.date() - timedelta(days=now_local.weekday())
    last_monday = this_monday - timedelta(days=7)
    week_start = timezone.make_aware(datetime.combine(last_monday, datetime.min.time()), USER_TIMEZONE)
    week_end = timezone.make_aware(datetime.combine(this_monday, datetime.min.time()), USER_TIMEZONE)

    posts_generated = Post.objects.filter(user=user, created_at__gte=week_start, created_at__lt=week_end).count()
    published_qs = Post.objects.filter(
        user=user, status='published', published_at__gte=week_start, published_at__lt=week_end,
    )
    posts_published = published_qs.count()

    week_analytics = list(Analytics.objects.filter(post__in=published_qs).select_related('post'))
    rates = [a.engagement_rate for a in week_analytics]
    avg_engagement_rate = round(sum(rates) / len(rates), 2) if rates else 0.0
    best = max(week_analytics, key=lambda a: a.engagement_rate, default=None)

    profile = getattr(user, 'profile', None)

    return {
        'posts_generated': posts_generated,
        'posts_published': posts_published,
        'avg_engagement_rate': avg_engagement_rate,
        'streak_current': profile.streak_current if profile else 0,
        'influence_score': profile.influence_score if profile else 0,
        'influence_score_trend': (profile.influence_score - profile.influence_score_previous) if profile else 0,
        'best_post': {
            'content_excerpt': best.post.content[:150], 'engagement_rate': best.engagement_rate,
        } if best else None,
    }


def _weekly_recommendation(stats: dict, user_id) -> str:
    prompt = f"""Voici les statistiques hebdomadaires d'un créateur de contenu sur Klark :
- Posts générés : {stats['posts_generated']}
- Posts publiés : {stats['posts_published']}
- Taux d'engagement moyen : {stats['avg_engagement_rate']}%
- Série en cours : {stats['streak_current']} jours
- Score d'influence : {stats['influence_score']} (variation : {stats['influence_score_trend']:+d})

En UNE phrase courte et actionnable, donne une recommandation personnalisée pour la
semaine à venir basée sur ces données (ou un mot d'encouragement adapté si aucun post
n'a été publié). Réponds uniquement avec la phrase, sans introduction."""

    model = select_model('weekly_digest')
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=model, max_tokens=150, messages=[{'role': 'user', 'content': prompt}],
    )
    log_ai_usage(
        model=model, tokens_in=message.usage.input_tokens, tokens_out=message.usage.output_tokens,
        task_type='weekly_digest', user_id=user_id,
    )
    return message.content[0].text.strip()


def build_weekly_digest_email_html(stats: dict, recommendation: str, unsubscribe_url: str) -> str:
    flame = ' 🔥' if stats['streak_current'] > 7 else ''
    if stats['best_post']:
        best_html = f'''
          <div style="background:#f9fafb;border-radius:8px;padding:16px;margin-bottom:16px;">
            <p style="margin:0 0 8px;color:#4b5563;">{stats['best_post']['content_excerpt']}</p>
            <p style="margin:0;font-weight:600;color:#111827;">{stats['best_post']['engagement_rate']}% d'engagement</p>
          </div>
        '''
    else:
        best_html = '<p style="color:#6b7280;">Aucun post publié cette semaine.</p>'

    trend = stats['influence_score_trend']
    trend_html = f"{'+' if trend >= 0 else ''}{trend}"

    return f'''
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:#4f46e5;padding:24px;text-align:center;">
        <h1 style="color:white;margin:0;font-size:20px;">📊 Klark — Votre semaine en chiffres</h1>
      </div>
      <div style="padding:24px;background:white;">
        <p style="color:#4b5563;">
          {stats['posts_generated']} posts générés · {stats['posts_published']} posts publiés ·
          {stats['avg_engagement_rate']}% d'engagement moyen
        </p>

        <h2 style="font-size:16px;color:#111827;">🏆 Votre meilleur post</h2>
        {best_html}

        <h2 style="font-size:16px;color:#111827;">🔥 Votre série</h2>
        <p style="color:#4b5563;">
          Série en cours : {stats['streak_current']} jours{flame} · Score d'influence : {stats['influence_score']} ({trend_html})
        </p>

        <h2 style="font-size:16px;color:#111827;">💡 Recommandation</h2>
        <p style="color:#4b5563;">{recommendation}</p>
      </div>
      <div style="padding:16px 24px;text-align:center;font-size:12px;color:#9ca3af;">
        <a href="{unsubscribe_url}" style="color:#9ca3af;">Se désabonner du digest hebdomadaire</a>
      </div>
    </div>
    '''


def maybe_send_weekly_digest(user) -> bool:
    """Envoie le digest hebdomadaire si weekly_digest est activé sur le profil.
    Retourne True si un email a effectivement été envoyé."""
    try:
        profile = user.profile
    except Profile.DoesNotExist:
        return False
    if not profile.weekly_digest:
        return False

    stats = gather_weekly_stats(user)
    recommendation = _weekly_recommendation(stats, user.id)
    unsubscribe_url = (
        f"{settings.FRONTEND_URL}/unsubscribe?type=weekly&token={make_weekly_unsubscribe_token(user.id)}"
    )
    html_message = build_weekly_digest_email_html(stats, recommendation, unsubscribe_url)

    send_mail(
        subject='Klark — Votre bilan hebdomadaire',
        message=strip_tags(html_message),
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
    return True
