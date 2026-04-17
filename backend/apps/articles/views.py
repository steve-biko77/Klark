from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Article
from .serializers import ArticleSerializer


class ArticleListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        articles = Article.objects.filter(source__user=request.user)
        return Response(ArticleSerializer(articles, many=True).data)
