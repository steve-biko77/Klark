from rest_framework import serializers
from .models import Post


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['id', 'article_id', 'content', 'platform', 'status', 'scheduled_at', 'created_at']
        read_only_fields = ['id', 'created_at']
