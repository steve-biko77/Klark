from django.utils.html import strip_tags
from rest_framework import serializers
from .models import Alert, Article, Notification


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


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = ['id', 'keyword', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class NotificationSerializer(serializers.ModelSerializer):
    article_title = serializers.CharField(source='article.title', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'article_id', 'article_title', 'keyword', 'is_read', 'created_at']
        read_only_fields = fields
