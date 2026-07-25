from django.utils.html import strip_tags
from rest_framework import serializers
from .models import Article


class ArticleSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)
    excerpt = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ['id', 'source_id', 'source_name', 'title', 'content', 'excerpt',
                  'url', 'score', 'published_at', 'created_at']
        read_only_fields = fields

    def get_excerpt(self, obj):
        return strip_tags(obj.content)[:150]
