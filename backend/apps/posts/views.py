import datetime
import json
import secrets
import urllib.parse
import urllib.request

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.shortcuts import get_object_or_404

from apps.articles.models import Article
from apps.authentication.models import Profile
from .models import Post, LinkedInToken
from .serializers import PostSerializer
from .services import generate_post
from .encryption import encrypt


class PostListView(APIView):

    def get(self, request):
        posts = Post.objects.filter(user=request.user)
        return Response(PostSerializer(posts, many=True).data)


class PostDetailView(APIView):

    def get(self, request, post_id):
        post = get_object_or_404(Post, id=post_id, user=request.user)
        return Response(PostSerializer(post).data)

    def patch(self, request, post_id):
        post = get_object_or_404(Post, id=post_id, user=request.user)
        serializer = PostSerializer(post, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostGenerateView(APIView):

    def post(self, request):
        article_id = request.data.get('article_id')
        platform = request.data.get('platform', 'linkedin')

        article = get_object_or_404(Article, id=article_id, source__user=request.user)

        try:
            style_prompt = request.user.profile.style_prompt
        except Profile.DoesNotExist:
            style_prompt = ''

        content = generate_post(
            article_title=article.title,
            article_content=article.content,
            platform=platform,
            style_prompt=style_prompt,
        )

        post = Post.objects.create(
            user=request.user,
            article=article,
            content=content,
            platform=platform,
            status='draft',
        )

        return Response(PostSerializer(post).data, status=status.HTTP_201_CREATED)


class PostCalendarView(APIView):

    def get(self, request):
        week_str = request.query_params.get('week')
        if not week_str:
            return Response({'error': 'week parameter required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ref_date = datetime.date.fromisoformat(week_str)
        except ValueError:
            return Response({'error': 'Invalid date format, use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

        monday = ref_date - datetime.timedelta(days=ref_date.weekday())
        monday_dt = timezone.make_aware(datetime.datetime(monday.year, monday.month, monday.day))
        sunday_dt = monday_dt + datetime.timedelta(days=7)

        posts = Post.objects.filter(
            user=request.user,
            scheduled_at__isnull=False,
            scheduled_at__gte=monday_dt,
            scheduled_at__lt=sunday_dt,
        )

        result = {}
        for post in posts:
            day_key = post.scheduled_at.date().isoformat()
            if day_key not in result:
                result[day_key] = []
            result[day_key].append(PostSerializer(post).data)

        return Response(result)


class PostScheduleView(APIView):

    CONFLICT_WINDOW_MINUTES = 30

    def patch(self, request, post_id):
        post = get_object_or_404(Post, id=post_id, user=request.user)

        scheduled_str = request.data.get('scheduled_at')
        force_conflict = bool(request.data.get('force_conflict', False))
        if not scheduled_str:
            return Response({'error': 'scheduled_at required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            naive_dt = datetime.datetime.fromisoformat(scheduled_str)
            aware_dt = timezone.make_aware(naive_dt) if timezone.is_naive(naive_dt) else naive_dt
        except ValueError:
            return Response({'error': 'Invalid datetime format'}, status=status.HTTP_400_BAD_REQUEST)

        if aware_dt <= timezone.now():
            return Response(
                {'error': 'Impossible de programmer dans le passé'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not force_conflict:
            window = datetime.timedelta(minutes=self.CONFLICT_WINDOW_MINUTES)
            conflict = Post.objects.filter(
                user=request.user,
                platform=post.platform,
                status='scheduled',
                scheduled_at__range=(aware_dt - window, aware_dt + window),
            ).exclude(pk=post.id).first()

            if conflict:
                return Response({
                    'warning': 'Conflit horaire détecté',
                    'conflicting_post_id': conflict.id,
                    'conflicting_time': conflict.scheduled_at,
                }, status=status.HTTP_200_OK)

        post.scheduled_at = aware_dt
        post.status = 'scheduled'
        post.save()

        return Response(PostSerializer(post).data)


# ── LinkedIn OAuth ──────────────────────────────────────────────────────────

class LinkedInAuthView(APIView):
    """
    GET /posts/linkedin/auth/?token=<jwt>
    Redirige vers l'URL d'autorisation LinkedIn.
    Le JWT est passé en query param car la vue est atteinte via navigation navigateur
    (window.location.href), pas via fetch avec Authorization header.
    En mode mock (LINKEDIN_CLIENT_ID=mock), redirige directement vers le callback.
    """
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        jwt_token = request.query_params.get('token', '')

        try:
            validated = UntypedToken(jwt_token)
            user_id = validated.get('user_id')
            if not user_id:
                raise TokenError('No user_id in token')
        except (InvalidToken, TokenError, Exception):
            return Response({'error': 'Token invalide'}, status=status.HTTP_401_UNAUTHORIZED)

        client_id = settings.LINKEDIN_CLIENT_ID
        state = f"{user_id}:{secrets.token_urlsafe(16)}"
        cache.set(f'linkedin_oauth_state:{state}', True, 600)

        if client_id == 'mock':
            callback_url = (
                f"{settings.LINKEDIN_REDIRECT_URI}"
                f"?code=mock&state={urllib.parse.quote(state)}"
            )
            return HttpResponseRedirect(callback_url)

        params = urllib.parse.urlencode({
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': settings.LINKEDIN_REDIRECT_URI,
            'scope': 'openid profile email w_member_social',
            'state': state,
        })
        return HttpResponseRedirect(f'https://www.linkedin.com/oauth/v2/authorization?{params}')


class LinkedInCallbackView(APIView):
    """
    GET /posts/linkedin/callback/?code=<code>&state=<user_id:nonce>
    Échange le code contre un access_token, chiffre et stocke.
    Redirige vers le frontend /settings?linkedin=connected (ou =error).
    """
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        code = request.query_params.get('code')
        state = request.query_params.get('state', '')
        error_url = f'{settings.FRONTEND_URL}/settings?linkedin=error'

        if not code or not state:
            return HttpResponseRedirect(error_url)

        state_key = f'linkedin_oauth_state:{state}'
        if not cache.get(state_key):
            return HttpResponseRedirect(error_url)
        cache.delete(state_key)

        try:
            user_id = int(state.split(':')[0])
            user = User.objects.get(id=user_id)
        except (ValueError, IndexError, User.DoesNotExist):
            return HttpResponseRedirect(error_url)

        try:
            if code == 'mock':
                expires_at = timezone.now() + datetime.timedelta(days=60)
                LinkedInToken.objects.update_or_create(
                    user=user,
                    defaults={
                        'access_token': encrypt('mock_access_token_klark_123'),
                        'token_type': 'Bearer',
                        'expires_at': expires_at,
                        'refresh_token': None,
                    },
                )
            else:
                data = urllib.parse.urlencode({
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': settings.LINKEDIN_REDIRECT_URI,
                    'client_id': settings.LINKEDIN_CLIENT_ID,
                    'client_secret': settings.LINKEDIN_CLIENT_SECRET,
                }).encode()

                req = urllib.request.Request(
                    'https://www.linkedin.com/oauth/v2/accessToken',
                    data=data,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    token_data = json.loads(resp.read())

                expires_at = timezone.now() + datetime.timedelta(
                    seconds=token_data.get('expires_in', 5_184_000)
                )
                refresh = token_data.get('refresh_token')
                LinkedInToken.objects.update_or_create(
                    user=user,
                    defaults={
                        'access_token': encrypt(token_data['access_token']),
                        'token_type': token_data.get('token_type', 'Bearer'),
                        'expires_at': expires_at,
                        'refresh_token': encrypt(refresh) if refresh else None,
                    },
                )
        except Exception:
            return HttpResponseRedirect(error_url)

        return HttpResponseRedirect(f'{settings.FRONTEND_URL}/settings?linkedin=connected')


class LinkedInStatusView(APIView):

    def get(self, request):
        try:
            token = request.user.linkedin_token
            return Response({
                'connected': True,
                'expires_at': token.expires_at.isoformat(),
            })
        except LinkedInToken.DoesNotExist:
            return Response({'connected': False, 'expires_at': None})


class LinkedInDisconnectView(APIView):

    def delete(self, request):
        try:
            request.user.linkedin_token.delete()
        except LinkedInToken.DoesNotExist:
            pass
        return Response({'disconnected': True})
