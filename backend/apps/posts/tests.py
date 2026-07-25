from unittest.mock import patch
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from apps.authentication.models import Profile
from apps.sources.models import Source
from apps.articles.models import Article
from apps.posts.models import Post


class PostsViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.client.force_authenticate(user=self.user)
        self.source = Source.objects.create(user=self.user, url='https://example.com/rss')
        self.article = Article.objects.create(
            source=self.source, title='Titre test', content='Contenu test', url='https://a.com'
        )

    def test_list_posts_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/posts/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_posts_only_user_owned(self):
        Post.objects.create(user=self.user, content='Mon post', platform='linkedin')
        other = User.objects.create_user(username='other', password='pass')
        Post.objects.create(user=other, content='Autre post', platform='twitter')

        response = self.client.get('/posts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    @patch('apps.posts.views.generate_post')
    def test_generate_post(self, mock_generate):
        mock_generate.return_value = 'Contenu généré par IA'
        data = {'article_id': self.article.id, 'platform': 'linkedin'}
        response = self.client.post('/posts/generate/', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], 'Contenu généré par IA')
        self.assertEqual(response.data['platform'], 'linkedin')
        self.assertEqual(Post.objects.filter(user=self.user).count(), 1)

    def test_generate_post_article_not_found(self):
        data = {'article_id': 9999, 'platform': 'linkedin'}
        response = self.client.post('/posts/generate/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('apps.posts.views.generate_post')
    def test_generate_post_injects_profile_style_prompt(self, mock_generate):
        mock_generate.return_value = 'Contenu'
        Profile.objects.create(
            user=self.user, persona='CREATEUR',
            style_prompt='Ton direct et punchy', sector='Tech', tone='DIRECT',
        )
        data = {'article_id': self.article.id, 'platform': 'linkedin'}
        self.client.post('/posts/generate/', data, format='json')

        self.assertEqual(mock_generate.call_args.kwargs['style_prompt'], 'Ton direct et punchy')

    @patch('apps.posts.views.generate_post')
    def test_generate_post_without_profile_uses_empty_style(self, mock_generate):
        mock_generate.return_value = 'Contenu'
        data = {'article_id': self.article.id, 'platform': 'linkedin'}
        response = self.client.post('/posts/generate/', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(mock_generate.call_args.kwargs['style_prompt'], '')

    def test_patch_post_updates_content(self):
        post = Post.objects.create(user=self.user, content='Brouillon initial', platform='linkedin')
        response = self.client.patch(f'/posts/{post.id}/', {'content': 'Contenu édité'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['content'], 'Contenu édité')
        post.refresh_from_db()
        self.assertEqual(post.content, 'Contenu édité')

    def test_patch_post_other_user_forbidden(self):
        other = User.objects.create_user(username='other2', password='pass')
        post = Post.objects.create(user=other, content='Pas à moi', platform='linkedin')
        response = self.client.patch(f'/posts/{post.id}/', {'content': 'Hack'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
