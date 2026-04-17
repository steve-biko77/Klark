from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Source
from .serializers import SourceSerializer
from .services import scrape_source


class SourceListCreateView(APIView):

    def get(self, request):
        sources = Source.objects.filter(user=request.user)
        return Response(SourceSerializer(sources, many=True).data)

    def post(self, request):
        serializer = SourceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, type='rss', status='pending')
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SourceScrapeView(APIView):

    def post(self, request, source_id):
        source = get_object_or_404(Source, id=source_id, user=request.user)
        result = scrape_source(source)
        return Response(result)
