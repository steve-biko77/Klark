from rest_framework import serializers
from .models import Source


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = ['id', 'url', 'name', 'type', 'status', 'last_crawled', 'created_at']
        read_only_fields = ['id', 'type', 'status', 'last_crawled', 'created_at']
