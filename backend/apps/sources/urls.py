from django.urls import path
from .views import SourceListCreateView, SourceScrapeView

urlpatterns = [
    path('', SourceListCreateView.as_view(), name='sources-list'),
    path('<int:source_id>/scrape/', SourceScrapeView.as_view(), name='source-scrape'),
]
