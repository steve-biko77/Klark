from django.urls import path
from .views import (
    PostListView, PostDetailView, PostGenerateView, PostGenerateMultiView, PostIngestView,
    PostCalendarView, PostScheduleView,
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
]
