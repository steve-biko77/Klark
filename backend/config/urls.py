from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

from apps.authentication.views import DashboardStatsView, ProfileView
from apps.articles.views import (
    AlertListCreateView, AlertDetailView, NotificationListView, NotificationMarkReadView,
    TodayBriefingView, BriefingListView, BriefingMarkReadView, SendDigestView, UnsubscribeDigestView,
)


def health(request):
    return JsonResponse({'status': 'ok', 'service': 'klark-api'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health, name='health'),
    path('auth/', include('apps.authentication.urls')),
    path('sources/', include('apps.sources.urls')),
    path('articles/', include('apps.articles.urls')),
    path('posts/', include('apps.posts.urls')),
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('alerts/', AlertListCreateView.as_view(), name='alerts-list'),
    path('alerts/<int:alert_id>/', AlertDetailView.as_view(), name='alert-detail'),
    path('notifications/', NotificationListView.as_view(), name='notifications-list'),
    path('notifications/<int:notification_id>/read/', NotificationMarkReadView.as_view(), name='notification-read'),
    path('briefings/today/', TodayBriefingView.as_view(), name='briefing-today'),
    path('briefings/send-digest/', SendDigestView.as_view(), name='briefing-send-digest'),
    path('briefings/unsubscribe/', UnsubscribeDigestView.as_view(), name='briefing-unsubscribe'),
    path('briefings/', BriefingListView.as_view(), name='briefings-list'),
    path('briefings/<int:briefing_id>/read/', BriefingMarkReadView.as_view(), name='briefing-read'),
]
