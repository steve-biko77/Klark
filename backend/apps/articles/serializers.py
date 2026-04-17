from rest_framework import serializers
from .models import Article


class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ['id', 'source_id', 'title', 'content', 'url', 'score', 'published_at', 'created_at']
        read_only_fields = fields
