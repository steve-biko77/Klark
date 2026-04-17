from django.urls import path
from .views import PostListView, PostGenerateView

urlpatterns = [
    path('', PostListView.as_view(), name='posts-list'),
    path('generate/', PostGenerateView.as_view(), name='posts-generate'),
]
