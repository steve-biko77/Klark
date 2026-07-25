from unittest.mock import patch

from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status

from apps.sources.models import Source
from apps.articles.models import Article
from apps.posts.models import Post


class GenerateMultiViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='multiuser', password='pass')
        self.client.force_authenticate(user=self.user)
        self.source = Source.objects.create(user=self.user, url='https://example.com/rss')
        self.article = Article.objects.create(
            source=self.source, title='Titre', content='Contenu', url='https://a.com'
        )

    @patch('apps.posts.views.generate_post')
    def test_generates_a_draft_per_platform(self, mock_generate):
        mock_generate.side_effect = lambda **kwargs: f"Post {kwargs['platform']}"

        response = self.client.post('/posts/generate-multi/', {
            'article_id': self.article.id,
            'platforms': ['linkedin', 'twitter'],
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(Post.objects.filter(user=self.user).count(), 2)

    @patch('apps.posts.views.generate_post')
    def test_uses_multi_format_task_type(self, mock_generate):
        mock_generate.return_value = 'Contenu'

        self.client.post('/posts/generate-multi/', {
            'article_id': self.article.id,
            'platforms': ['linkedin'],
        }, format='json')

        self.assertEqual(mock_generate.call_args.kwargs['task_type'], 'multi_format')

    @patch('apps.posts.views.generate_post')
    def test_partial_failure_keeps_other_platforms(self, mock_generate):
        def side_effect(**kwargs):
            if kwargs['platform'] == 'twitter':
                raise Exception('Timeout')
            return f"Post {kwargs['platform']}"

        mock_generate.side_effect = side_effect

        response = self.client.post('/posts/generate-multi/', {
            'article_id': self.article.id,
            'platforms': ['linkedin', 'twitter'],
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        results_by_platform = {r['platform']: r for r in response.data['results']}
        self.assertIn('content', results_by_platform['linkedin'])
        self.assertIn('error', results_by_platform['twitter'])
        self.assertEqual(Post.objects.filter(user=self.user).count(), 1)

    def test_requires_platforms(self):
        response = self.client.post('/posts/generate-multi/', {
            'article_id': self.article.id,
            'platforms': [],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_article_not_found(self):
        response = self.client.post('/posts/generate-multi/', {
            'article_id': 9999,
            'platforms': ['linkedin'],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
