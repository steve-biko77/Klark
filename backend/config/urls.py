from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

from apps.authentication.views import DashboardStatsView


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
]
