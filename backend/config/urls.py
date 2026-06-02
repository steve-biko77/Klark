from django.urls import path, include
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


def health(request):
    return JsonResponse({'status': 'ok', 'service': 'klark-api'})


urlpatterns = [
    path('health/', health, name='health'),
    path('auth/', include('apps.authentication.urls')),
    path('sources/', include('apps.sources.urls')),
    path('articles/', include('apps.articles.urls')),
    path('posts/', include('apps.posts.urls')),
]