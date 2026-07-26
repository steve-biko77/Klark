import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .encryption import decrypt, encrypt

# Backoff exponentiel sur rate limit LinkedIn (429) : 1min, 5min, 15min.
RATE_LIMIT_BACKOFF_SECONDS = [60, 300, 900]


def _call_linkedin_api(access_token: str, method: str, path: str, json_body: dict | None = None):
    """Appelle l'API LinkedIn v2. Retourne le JSON décodé pour GET /v2/me, ou
    un tuple (post_urn, status_code) pour POST /v2/ugcPosts."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0',
    }
    data = json.dumps(json_body).encode() if json_body is not None else None
    req = urllib.request.Request(
        f'https://api.linkedin.com{path}', data=data, headers=headers, method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if path == '/v2/me':
                return json.loads(resp.read())
            return resp.headers.get('x-restli-id', ''), resp.status
    except urllib.error.HTTPError as e:
        if path == '/v2/me':
            raise
        return None, e.code


def _refresh_linkedin_token(li_token) -> str | None:
    """Rafraîchit un token LinkedIn expiré. Sauvegarde le nouveau token
    (chiffré) sur succès. Retourne le nouvel access_token en clair, ou None
    si le refresh échoue."""
    if not li_token.refresh_token:
        return None

    data = urllib.parse.urlencode({
        'grant_type': 'refresh_token',
        'refresh_token': decrypt(li_token.refresh_token),
        'client_id': settings.LINKEDIN_CLIENT_ID,
        'client_secret': settings.LINKEDIN_CLIENT_SECRET,
    }).encode()
    req = urllib.request.Request(
        'https://www.linkedin.com/oauth/v2/accessToken', data=data,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            token_data = json.loads(resp.read())
    except Exception:
        return None

    new_access_token = token_data.get('access_token')
    if not new_access_token:
        return None

    li_token.access_token = encrypt(new_access_token)
    li_token.expires_at = timezone.now() + timedelta(seconds=token_data.get('expires_in', 5_184_000))
    new_refresh = token_data.get('refresh_token')
    if new_refresh:
        li_token.refresh_token = encrypt(new_refresh)
    li_token.save()
    return new_access_token


@shared_task(bind=True, max_retries=3)
def publish_post_task(self, post_id: int) -> dict:
    """Publie un post programmé sur LinkedIn (SCRUM-22). Exécutée par Celery à
    l'heure exacte (eta=post.scheduled_at, cf. apps.posts.views.PostScheduleView).

    En mode mock (LINKEDIN_CLIENT_ID='mock', valeur par défaut en dev — cf.
    LinkedInAuthView/LinkedInCallbackView), simule une publication réussie sans
    appel réseau, cohérent avec le reste du flow OAuth déjà mocké."""
    from .models import LinkedInToken, Post

    try:
        post = Post.objects.get(id=post_id, status='scheduled')
    except Post.DoesNotExist:
        return {'status': 'skipped', 'reason': 'Post non trouvé ou déjà publié/annulé'}

    try:
        li_token = LinkedInToken.objects.get(user=post.user)
    except LinkedInToken.DoesNotExist:
        post.status = 'failed'
        post.save(update_fields=['status'])
        return {'status': 'failed', 'reason': 'Aucun token LinkedIn'}

    if settings.LINKEDIN_CLIENT_ID == 'mock':
        post.status = 'published'
        post.published_at = timezone.now()
        post.post_urn = f'urn:li:share:mock{post.id}'
        post.save(update_fields=['status', 'published_at', 'post_urn'])
        return {'status': 'published', 'post_urn': post.post_urn}

    access_token = decrypt(li_token.access_token)

    if li_token.expires_at <= timezone.now():
        new_access_token = _refresh_linkedin_token(li_token)
        if not new_access_token:
            post.status = 'failed'
            post.save(update_fields=['status'])
            return {'status': 'failed', 'reason': 'Refresh token échoué'}
        access_token = new_access_token

    me = _call_linkedin_api(access_token, 'GET', '/v2/me')
    person_urn = f"urn:li:person:{me['id']}"

    payload = {
        'author': person_urn,
        'lifecycleState': 'PUBLISHED',
        'specificContent': {
            'com.linkedin.ugc.ShareContent': {
                'shareCommentary': {'text': post.content},
                'shareMediaCategory': 'NONE',
            },
        },
        'visibility': {'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'},
    }
    post_urn, status_code = _call_linkedin_api(access_token, 'POST', '/v2/ugcPosts', json_body=payload)

    if status_code == 201:
        post.status = 'published'
        post.published_at = timezone.now()
        post.post_urn = post_urn
        post.save(update_fields=['status', 'published_at', 'post_urn'])
        return {'status': 'published', 'post_urn': post_urn}

    if status_code == 429:
        if self.request.retries >= self.max_retries:
            post.status = 'failed'
            post.save(update_fields=['status'])
            return {'status': 'failed', 'reason': 'Rate limit LinkedIn — max retries dépassé'}
        countdown = RATE_LIMIT_BACKOFF_SECONDS[min(self.request.retries, len(RATE_LIMIT_BACKOFF_SECONDS) - 1)]
        raise self.retry(countdown=countdown, exc=Exception('Rate limit LinkedIn'))

    post.status = 'failed'
    post.save(update_fields=['status'])
    return {'status': 'failed', 'code': status_code}
