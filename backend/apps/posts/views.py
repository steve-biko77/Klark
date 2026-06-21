import datetime

from django.utils import timezone
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


class PostCalendarView(APIView):

    def get(self, request):
        week_str = request.query_params.get('week')
        if not week_str:
            return Response({'error': 'week parameter required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ref_date = datetime.date.fromisoformat(week_str)
        except ValueError:
            return Response({'error': 'Invalid date format, use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

        monday = ref_date - datetime.timedelta(days=ref_date.weekday())
        monday_dt = timezone.make_aware(datetime.datetime(monday.year, monday.month, monday.day))
        sunday_dt = monday_dt + datetime.timedelta(days=7)

        posts = Post.objects.filter(
            user=request.user,
            scheduled_at__isnull=False,
            scheduled_at__gte=monday_dt,
            scheduled_at__lt=sunday_dt,
        )

        result = {}
        for post in posts:
            day_key = post.scheduled_at.date().isoformat()
            if day_key not in result:
                result[day_key] = []
            result[day_key].append(PostSerializer(post).data)

        return Response(result)


class PostScheduleView(APIView):

    def patch(self, request, post_id):
        post = get_object_or_404(Post, id=post_id, user=request.user)

        scheduled_str = request.data.get('scheduled_at')
        if not scheduled_str:
            return Response({'error': 'scheduled_at required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            naive_dt = datetime.datetime.fromisoformat(scheduled_str)
            aware_dt = timezone.make_aware(naive_dt) if timezone.is_naive(naive_dt) else naive_dt
        except ValueError:
            return Response({'error': 'Invalid datetime format'}, status=status.HTTP_400_BAD_REQUEST)

        post.scheduled_at = aware_dt
        post.status = 'scheduled'
        post.save()

        return Response(PostSerializer(post).data)
