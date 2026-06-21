from django.urls import path
from .views import PostListView, PostDetailView, PostGenerateView

urlpatterns = [
    path('', PostListView.as_view(), name='posts-list'),
    path('<int:post_id>/', PostDetailView.as_view(), name='post-detail'),
    path('generate/', PostGenerateView.as_view(), name='posts-generate'),
]
