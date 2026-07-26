from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

from apps.authentication.views import (
    DashboardStatsView, ProfileView, GamificationView, LearnStyleView, ResetStyleView,
)
from apps.articles.views import (
    AlertListCreateView, AlertDetailView, NotificationListView, NotificationMarkReadView,
    TodayBriefingView, BriefingListView, BriefingMarkReadView, SendDigestView, UnsubscribeDigestView,
    SendWeeklyDigestView, UnsubscribeWeeklyDigestView,
)
from apps.posts.views import AnalyticsCollectView, AnalyticsOverviewView, AnalyticsRecommendationsView
from apps.sources.views import TopicPackListView, TopicPackActivateView


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
    path('briefings/send-weekly-digest/', SendWeeklyDigestView.as_view(), name='briefing-send-weekly-digest'),
    path('briefings/unsubscribe-weekly/', UnsubscribeWeeklyDigestView.as_view(), name='briefing-unsubscribe-weekly'),
    path('gamification/', GamificationView.as_view(), name='gamification'),
    path('profile/learn-style/', LearnStyleView.as_view(), name='profile-learn-style'),
    path('profile/reset-style/', ResetStyleView.as_view(), name='profile-reset-style'),
    path('analytics/', AnalyticsOverviewView.as_view(), name='analytics-overview'),
    path('analytics/collect/', AnalyticsCollectView.as_view(), name='analytics-collect'),
    path('analytics/recommendations/', AnalyticsRecommendationsView.as_view(), name='analytics-recommendations'),
    path('topic-packs/', TopicPackListView.as_view(), name='topic-packs-list'),
    path('topic-packs/<int:pack_id>/activate/', TopicPackActivateView.as_view(), name='topic-pack-activate'),
]
