from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from apps.authentication.models import Profile
from .models import Alert, Article, DailyBriefing, Notification
from .serializers import AlertSerializer, ArticleSerializer, DailyBriefingSerializer, NotificationSerializer
from .services import (
    generate_daily_briefing, maybe_send_daily_digest, verify_unsubscribe_token,
    maybe_send_weekly_digest, verify_weekly_unsubscribe_token,
)

MAX_ACTIVE_ALERTS = 10


class ArticleListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        articles = Article.objects.filter(source__user=request.user)
        return Response(ArticleSerializer(articles, many=True).data)


class ArticleDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, article_id):
        article = get_object_or_404(Article, id=article_id, source__user=request.user)
        return Response(ArticleSerializer(article).data)


class AlertListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        alerts = Alert.objects.filter(user=request.user)
        return Response(AlertSerializer(alerts, many=True).data)

    def post(self, request):
        active_count = Alert.objects.filter(user=request.user, is_active=True).count()
        if active_count >= MAX_ACTIVE_ALERTS:
            return Response(
                {'error': f'Maximum {MAX_ACTIVE_ALERTS} alertes actives par utilisateur'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = AlertSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AlertDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, alert_id):
        alert = get_object_or_404(Alert, id=alert_id, user=request.user)

        activating = request.data.get('is_active') and not alert.is_active
        if activating:
            active_count = Alert.objects.filter(user=request.user, is_active=True).count()
            if active_count >= MAX_ACTIVE_ALERTS:
                return Response(
                    {'error': f'Maximum {MAX_ACTIVE_ALERTS} alertes actives par utilisateur'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = AlertSerializer(alert, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, alert_id):
        alert = get_object_or_404(Alert, id=alert_id, user=request.user)
        alert.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)
        return Response(NotificationSerializer(notifications, many=True).data)


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, notification_id):
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response(NotificationSerializer(notification).data)


class TodayBriefingView(APIView):
    """Génère (déclenchement paresseux, à la demande) et retourne le briefing flash
    du jour pour les Traders. None pour tout autre persona ou profil absent.

    Déviation assumée : le prompt technique décrit une tâche Celery Beat à 7h,
    mais l'infra Celery est en cours de construction ailleurs (SCRUM-22) — génération
    à la demande au premier chargement du dashboard plutôt que planifiée."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return Response(None)

        if profile.persona != 'TRADER':
            return Response(None)

        briefing = generate_daily_briefing(request.user)
        return Response(DailyBriefingSerializer(briefing).data)


class BriefingListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        briefings = DailyBriefing.objects.filter(user=request.user)
        return Response(DailyBriefingSerializer(briefings, many=True).data)


class BriefingMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, briefing_id):
        briefing = get_object_or_404(DailyBriefing, id=briefing_id, user=request.user)
        briefing.is_read = True
        briefing.save(update_fields=['is_read'])
        return Response(DailyBriefingSerializer(briefing).data)


class SendDigestView(APIView):
    """Déclenchement manuel de l'envoi du digest email (respecte la préférence
    email_digest de l'utilisateur). Déviation assumée : le prompt technique décrit
    un envoi automatique à 7h via Celery Beat, non disponible pour la même raison
    que TodayBriefingView (SCRUM-22 en cours ailleurs)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sent = maybe_send_daily_digest(request.user)
        return Response({'sent': sent})


class UnsubscribeDigestView(APIView):
    """Lien de désabonnement cliqué depuis l'email — pas d'authentification requise,
    le token signé (30 jours) identifie l'utilisateur."""
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        token = request.query_params.get('token', '')
        user_id = verify_unsubscribe_token(token) if token else None
        if not user_id:
            return Response({'error': 'Lien invalide ou expiré'}, status=status.HTTP_400_BAD_REQUEST)

        Profile.objects.filter(user_id=user_id).update(email_digest=False)
        return Response({'unsubscribed': True})


class SendWeeklyDigestView(APIView):
    """Déclenchement manuel de l'envoi du digest hebdomadaire (SCRUM-40) —
    déviation assumée : le prompt technique décrit un envoi automatique chaque
    lundi 8h via Celery Beat, non disponible (SCRUM-22 en cours ailleurs)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sent = maybe_send_weekly_digest(request.user)
        return Response({'sent': sent})


class UnsubscribeWeeklyDigestView(APIView):
    """Lien de désabonnement spécifique au digest hebdomadaire — jeton distinct
    de celui du digest matinal (SCRUM-32), pas d'authentification requise."""
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        token = request.query_params.get('token', '')
        user_id = verify_weekly_unsubscribe_token(token) if token else None
        if not user_id:
            return Response({'error': 'Lien invalide ou expiré'}, status=status.HTTP_400_BAD_REQUEST)

        Profile.objects.filter(user_id=user_id).update(weekly_digest=False)
        return Response({'unsubscribed': True})
