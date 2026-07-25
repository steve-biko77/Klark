from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import Alert, Article, Notification
from .serializers import AlertSerializer, ArticleSerializer, NotificationSerializer

MAX_ACTIVE_ALERTS = 10


class ArticleListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        articles = Article.objects.filter(source__user=request.user)
        return Response(ArticleSerializer(articles, many=True).data)


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
