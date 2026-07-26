from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Source
from .serializers import SourceSerializer
from .services import detect_feed_urls, scrape_source


class SourceListCreateView(APIView):

    def get(self, request):
        sources = Source.objects.filter(user=request.user)
        return Response(SourceSerializer(sources, many=True).data)

    def post(self, request):
        url = request.data.get('url', '')
        candidates = detect_feed_urls(url) if url else []

        if not candidates:
            return Response(
                {'url': "Aucun flux RSS détecté sur cette URL"}, status=status.HTTP_400_BAD_REQUEST,
            )
        if len(candidates) > 1:
            return Response({'candidates': candidates}, status=status.HTTP_200_OK)

        data = {**request.data, 'url': candidates[0]}
        serializer = SourceSerializer(data=data)
        if serializer.is_valid():
            serializer.save(user=request.user, type='rss', status='pending')
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SourceDetectView(APIView):
    """Détecte le(s) flux RSS d'une URL sans créer de source — utilisé par le
    frontend pour afficher un aperçu/sélecteur avant confirmation (SCRUM-24),
    et par l'activation des Topic Packs (SCRUM-27)."""

    def post(self, request):
        url = request.data.get('url', '')
        if not url:
            return Response({'error': 'url requis'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'candidates': detect_feed_urls(url)})


class SourceDetailView(APIView):

    def patch(self, request, source_id):
        source = get_object_or_404(Source, id=source_id, user=request.user)
        serializer = SourceSerializer(source, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, source_id):
        source = get_object_or_404(Source, id=source_id, user=request.user)
        source.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SourceScrapeView(APIView):

    def post(self, request, source_id):
        source = get_object_or_404(Source, id=source_id, user=request.user)
        result = scrape_source(source)
        return Response(result)
