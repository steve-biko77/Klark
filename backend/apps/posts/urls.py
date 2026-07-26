from django.urls import path
from .views import (
    PostListView, PostDetailView, PostGenerateView, PostGenerateMultiView, PostIngestView,
    PostAICommandView, PostCalendarView, PostScheduleView, PostCancelView, PostRetryView,
    LinkedInAuthView, LinkedInCallbackView, LinkedInStatusView, LinkedInDisconnectView,
)

urlpatterns = [
    path('', PostListView.as_view(), name='posts-list'),
    path('calendar/', PostCalendarView.as_view(), name='posts-calendar'),
    path('generate/', PostGenerateView.as_view(), name='posts-generate'),
    path('generate-multi/', PostGenerateMultiView.as_view(), name='posts-generate-multi'),
    path('ingest/', PostIngestView.as_view(), name='posts-ingest'),
    path('linkedin/auth/', LinkedInAuthView.as_view(), name='linkedin-auth'),
    path('linkedin/callback/', LinkedInCallbackView.as_view(), name='linkedin-callback'),
    path('linkedin/status/', LinkedInStatusView.as_view(), name='linkedin-status'),
    path('linkedin/disconnect/', LinkedInDisconnectView.as_view(), name='linkedin-disconnect'),
    path('<int:post_id>/', PostDetailView.as_view(), name='post-detail'),
    path('<int:post_id>/schedule/', PostScheduleView.as_view(), name='post-schedule'),
    path('<int:post_id>/cancel/', PostCancelView.as_view(), name='post-cancel'),
    path('<int:post_id>/retry/', PostRetryView.as_view(), name='post-retry'),
    path('<int:post_id>/ai-command/', PostAICommandView.as_view(), name='post-ai-command'),
]

# NB : les routes /analytics/* et /gamification/ sont montées au niveau racine
# (config/urls.py), pas ici, pour matcher les chemins attendus côté frontend.
