from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from apps.sources.models import Source
from apps.articles.models import Article


class ArticlesViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.client.force_authenticate(user=self.user)
        self.source = Source.objects.create(user=self.user, url='https://example.com/rss')

    def test_list_articles_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/articles/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_articles_returns_only_user_articles(self):
        Article.objects.create(source=self.source, title='Mon article', url='https://a.com')

        other_user = User.objects.create_user(username='other', password='pass')
        other_source = Source.objects.create(user=other_user, url='https://other.com/rss')
        Article.objects.create(source=other_source, title='Autre article', url='https://b.com')

        response = self.client.get('/articles/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Mon article')

    def test_list_articles_empty_if_no_sources(self):
        user2 = User.objects.create_user(username='user2', password='pass')
        self.client.force_authenticate(user=user2)
        response = self.client.get('/articles/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])
