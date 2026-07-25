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

    def test_articles_sorted_by_published_date_desc(self):
        from datetime import timedelta
        from django.utils import timezone

        older = Article.objects.create(
            source=self.source, title='Vieux', url='https://a.com/1',
            published_at=timezone.now() - timedelta(days=2),
        )
        newer = Article.objects.create(
            source=self.source, title='Récent', url='https://a.com/2',
            published_at=timezone.now(),
        )

        response = self.client.get('/articles/')
        ids = [a['id'] for a in response.data]
        self.assertEqual(ids, [newer.id, older.id])

    def test_article_includes_source_name_and_stripped_excerpt(self):
        source = Source.objects.create(user=self.user, url='https://example.com/rss2', name='Ma Source')
        Article.objects.create(
            source=source, title='Titre', url='https://a.com/3',
            content='<p>Contenu <strong>riche</strong> avec balises</p>' + 'x' * 200,
        )

        response = self.client.get('/articles/')
        article = response.data[0]
        self.assertEqual(article['source_name'], 'Ma Source')
        self.assertNotIn('<p>', article['excerpt'])
        self.assertNotIn('<strong>', article['excerpt'])
        self.assertLessEqual(len(article['excerpt']), 150)
