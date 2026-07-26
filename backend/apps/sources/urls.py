from django.urls import path
from .views import SourceListCreateView, SourceDetailView, SourceScrapeView, SourceDetectView

urlpatterns = [
    path('', SourceListCreateView.as_view(), name='sources-list'),
    path('detect/', SourceDetectView.as_view(), name='sources-detect'),
    path('<int:source_id>/', SourceDetailView.as_view(), name='source-detail'),
    path('<int:source_id>/scrape/', SourceScrapeView.as_view(), name='source-scrape'),
]
