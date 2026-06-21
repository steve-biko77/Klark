from django.urls import path
from .views import PostListView, PostDetailView, PostGenerateView, PostCalendarView, PostScheduleView

urlpatterns = [
    path('', PostListView.as_view(), name='posts-list'),
    path('calendar/', PostCalendarView.as_view(), name='posts-calendar'),
    path('generate/', PostGenerateView.as_view(), name='posts-generate'),
    path('<int:post_id>/', PostDetailView.as_view(), name='post-detail'),
    path('<int:post_id>/schedule/', PostScheduleView.as_view(), name='post-schedule'),
]
