from django.urls import path, include
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    return Response({'status': 'ok', 'service': 'klark-api'})


urlpatterns = [
    path('health/', health, name='health'),
    path('auth/', include('apps.authentication.urls')),
    # path('sources/', include('apps.sources.urls')),  # Task 6
    # path('articles/', include('apps.articles.urls')),  # Task 7
    # path('posts/', include('apps.posts.urls')),  # Task 8
]
