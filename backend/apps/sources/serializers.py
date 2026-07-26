from rest_framework import serializers
from .models import Source, TopicPack


class TopicPackSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopicPack
        fields = ['id', 'name', 'description', 'persona', 'sources']


class SourceSerializer(serializers.ModelSerializer):
    articles_count = serializers.SerializerMethodField()

    class Meta:
        model = Source
        fields = ['id', 'url', 'name', 'type', 'status', 'last_crawled', 'created_at', 'articles_count']
        read_only_fields = ['id', 'type', 'status', 'last_crawled', 'created_at', 'articles_count']

    def get_articles_count(self, obj):
        return obj.articles.count()
