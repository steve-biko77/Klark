import random
from datetime import timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from apps.articles.models import Article
from apps.posts.models import Post
from apps.sources.models import Source
from .models import OTPCode, Profile
from .serializers import ProfileSerializer, RegisterSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """Connexion avec 2FA par email — retourne un OTP au lieu des tokens."""
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username', '')
        password = request.data.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({'error': 'Identifiants invalides'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.email:
            return Response(
                {'error': 'Aucune adresse email associée à ce compte. Impossible d\'envoyer le code 2FA.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        expires_at = timezone.now() + timedelta(minutes=10)

        OTPCode.objects.filter(user=user).delete()
        OTPCode.objects.create(user=user, code=code, expires_at=expires_at)

        send_mail(
            subject='Votre code de connexion Klark',
            message=(
                f'Bonjour {user.username},\n\n'
                f'Votre code de connexion est : {code}\n\n'
                f'Ce code expire dans 10 minutes.\n'
                f'Si vous n\'avez pas demandé ce code, ignorez cet email.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

        return Response({
            'status': 'otp_sent',
            'user_id': user.id,
            'email': user.email,
            'username': user.username,
        })


class VerifyOTPView(APIView):
    """Vérifie le code OTP et retourne les tokens JWT."""
    permission_classes = [AllowAny]

    MAX_ATTEMPTS = 3
    LOCKOUT_SECONDS = 15 * 60

    def post(self, request):
        user_id = request.data.get('user_id')
        code = request.data.get('code', '').strip()

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'}, status=status.HTTP_400_BAD_REQUEST)

        lockout_key = f'otp_lockout:{user.id}'
        if cache.get(lockout_key):
            return Response(
                {'error': 'Trop de tentatives échouées. Réessayez dans 15 minutes.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        try:
            otp = OTPCode.objects.get(user=user, code=code, used=False)
        except OTPCode.DoesNotExist:
            self._register_failed_attempt(user.id)
            return Response({'error': 'Code invalide'}, status=status.HTTP_400_BAD_REQUEST)

        if otp.expires_at < timezone.now():
            self._register_failed_attempt(user.id)
            return Response({'error': 'Code expiré — demandez un nouveau code'}, status=status.HTTP_400_BAD_REQUEST)

        otp.used = True
        otp.save()
        cache.delete(f'otp_attempts:{user.id}')
        cache.delete(lockout_key)

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'username': user.username,
        })

    @classmethod
    def _register_failed_attempt(cls, user_id):
        attempts_key = f'otp_attempts:{user_id}'
        attempts = cache.get(attempts_key, 0) + 1
        cache.set(attempts_key, attempts, cls.LOCKOUT_SECONDS)
        if attempts >= cls.MAX_ATTEMPTS:
            cache.set(f'otp_lockout:{user_id}', True, cls.LOCKOUT_SECONDS)


class ResendOTPView(APIView):
    """Renvoie un nouveau code OTP à l'utilisateur."""
    permission_classes = [AllowAny]

    def post(self, request):
        user_id = request.data.get('user_id')

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'}, status=status.HTTP_400_BAD_REQUEST)

        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        expires_at = timezone.now() + timedelta(minutes=10)

        OTPCode.objects.filter(user=user).delete()
        OTPCode.objects.create(user=user, code=code, expires_at=expires_at)

        send_mail(
            subject='Votre nouveau code de connexion Klark',
            message=(
                f'Bonjour {user.username},\n\n'
                f'Votre nouveau code de connexion est : {code}\n\n'
                f'Ce code expire dans 10 minutes.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

        return Response({'status': 'otp_sent'})


class PasswordResetRequestView(APIView):
    """Envoie un lien de réinitialisation de mot de passe par email."""
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip()
        # Même réponse que l'email existe ou non (sécurité)
        generic_response = Response({
            'message': 'Si cette adresse email existe, vous recevrez un lien de réinitialisation.'
        })

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return generic_response

        token = PasswordResetTokenGenerator().make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"

        send_mail(
            subject='Réinitialisation de votre mot de passe Klark',
            message=(
                f'Bonjour {user.username},\n\n'
                f'Cliquez sur ce lien pour réinitialiser votre mot de passe :\n\n'
                f'{reset_link}\n\n'
                f'Ce lien expire dans 24 heures.\n'
                f'Si vous n\'avez pas demandé cette réinitialisation, ignorez cet email.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

        return generic_response


class PasswordResetConfirmView(APIView):
    """Confirme le reset du mot de passe avec uid + token + nouveau mot de passe."""
    permission_classes = [AllowAny]

    def post(self, request):
        uid = request.data.get('uid', '')
        token = request.data.get('token', '')
        new_password = request.data.get('new_password', '')

        try:
            user_pk = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_pk)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'error': 'Lien invalide'}, status=status.HTTP_400_BAD_REQUEST)

        if not PasswordResetTokenGenerator().check_token(user, token):
            return Response({'error': 'Lien invalide ou expiré'}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response(
                {'error': 'Le mot de passe doit contenir au moins 8 caractères'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()

        return Response({'message': 'Mot de passe réinitialisé avec succès'})


class DashboardStatsView(APIView):
    """Retourne les vrais stats de l'utilisateur connecté pour le dashboard."""

    def get(self, request):
        user = request.user
        return Response({
            'sources_actives': Source.objects.filter(user=user, status='active').count(),
            'posts_generes': Post.objects.filter(user=user).count(),
            'articles': Article.objects.filter(source__user=user).count(),
        })


class ProfileView(APIView):
    """
    Profil éditorial de l'utilisateur (persona, secteur, ton, style_prompt).
    Utilisé par la génération de posts (style_prompt, cf. apps.posts.services.generate_post)
    et par le scoring sémantique des articles (persona + secteur).
    Créé à la volée avec des valeurs par défaut s'il n'existe pas encore.
    """

    def get(self, request):
        profile, _ = Profile.objects.get_or_create(
            user=request.user,
            defaults={'persona': 'CREATEUR', 'tone': 'EXPERT', 'style_prompt': '', 'sector': ''},
        )
        return Response(ProfileSerializer(profile).data)

    def patch(self, request):
        profile, _ = Profile.objects.get_or_create(
            user=request.user,
            defaults={'persona': 'CREATEUR', 'tone': 'EXPERT', 'style_prompt': '', 'sector': ''},
        )
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            if 'style_prompt' in request.data:
                # L'édition manuelle du style_prompt devient la nouvelle valeur
                # de référence pour le bouton "Réinitialiser" (SCRUM-39).
                profile.style_prompt_manual = serializer.validated_data.get('style_prompt', '')
                profile.save(update_fields=['style_prompt_manual'])
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GamificationView(APIView):
    """Widget dashboard : streak éditorial + score d'influence (SCRUM-37). Le
    streak est toujours recalculé à la demande depuis Post.published_at ; le
    score d'influence n'est recalculé que si la dernière mise à jour date de
    plus de 7 jours (équivalent hebdomadaire, cf. services.maybe_update_influence_score)."""

    def get(self, request):
        from apps.posts.services import maybe_update_influence_score, should_remind_publish_today, update_streak

        update_streak(request.user)
        profile = maybe_update_influence_score(request.user)
        return Response({
            'streak_current': profile.streak_current,
            'streak_max': profile.streak_max,
            'influence_score': profile.influence_score,
            'influence_score_previous': profile.influence_score_previous,
            'influence_score_trend': profile.influence_score - profile.influence_score_previous,
            'remind_publish_today': should_remind_publish_today(request.user),
        })


class LearnStyleView(APIView):
    """Déclenchement manuel de l'apprentissage de style (SCRUM-39) — déviation
    assumée : la tâche Celery Beat dimanche 23h n'est pas disponible tant que
    SCRUM-22 n'est pas mergé."""

    def post(self, request):
        from apps.posts.services import update_style_memory

        profile = update_style_memory(request.user)
        if profile is None:
            return Response({'updated': False, 'message': 'Pas assez de posts publiés (minimum 5).'})
        return Response({'updated': True, **ProfileSerializer(profile).data})


class ResetStyleView(APIView):

    def post(self, request):
        from apps.posts.services import reset_style_prompt

        profile = reset_style_prompt(request.user)
        return Response(ProfileSerializer(profile).data)
