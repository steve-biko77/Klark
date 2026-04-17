from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from apps.articles.models import Article
from .models import Post
from .serializers import PostSerializer
from .services import generate_post


class PostListView(APIView):

    def get(self, request):
        posts = Post.objects.filter(user=request.user)
        return Response(PostSerializer(posts, many=True).data)


class PostGenerateView(APIView):

    def post(self, request):
        article_id = request.data.get('article_id')
        platform = request.data.get('platform', 'linkedin')

        article = get_object_or_404(Article, id=article_id, source__user=request.user)

        content = generate_post(
            article_title=article.title,
            article_content=article.content,
            platform=platform,
        )

        post = Post.objects.create(
            user=request.user,
            article=article,
            content=content,
            platform=platform,
            status='draft',
        )

        return Response(PostSerializer(post).data, status=status.HTTP_201_CREATED)
