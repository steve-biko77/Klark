from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs
from django.contrib.auth.models import User
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from apps.authentication.models import Profile
from apps.sources.models import Source
from apps.articles.models import Article
from apps.posts.models import Post, LinkedInToken
from apps.posts.encryption import decrypt


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
    def test_generate_post_ai_failure_returns_503_not_500(self, mock_generate):
        mock_generate.side_effect = Exception('Error code: 401 - invalid x-api-key')
        data = {'article_id': self.article.id, 'platform': 'linkedin'}

        response = self.client.post('/posts/generate/', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn('error', response.data)
        self.assertEqual(Post.objects.filter(user=self.user).count(), 0)

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


class ScheduleEndpointTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='scheduser', password='pass')
        self.client.force_authenticate(user=self.user)

    def test_schedule_rejects_past_date(self):
        post = Post.objects.create(user=self.user, content='Post', platform='linkedin')
        past = (timezone.now() - timedelta(days=1)).isoformat()

        response = self.client.patch(f'/posts/{post.id}/schedule/', {'scheduled_at': past}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        post.refresh_from_db()
        self.assertEqual(post.status, 'draft')

    def test_schedule_success_no_conflict(self):
        post = Post.objects.create(user=self.user, content='Post', platform='linkedin')
        future = (timezone.now() + timedelta(days=1)).isoformat()

        response = self.client.patch(f'/posts/{post.id}/schedule/', {'scheduled_at': future}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'scheduled')

    def test_schedule_detects_conflict_same_platform_within_30min(self):
        slot = timezone.now() + timedelta(days=1)
        Post.objects.create(
            user=self.user, content='Déjà programmé', platform='linkedin',
            status='scheduled', scheduled_at=slot,
        )
        post = Post.objects.create(user=self.user, content='Nouveau', platform='linkedin')
        nearby = (slot + timedelta(minutes=20)).isoformat()

        response = self.client.patch(f'/posts/{post.id}/schedule/', {'scheduled_at': nearby}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('warning', response.data)
        post.refresh_from_db()
        self.assertEqual(post.status, 'draft')

    def test_schedule_no_conflict_different_platform(self):
        slot = timezone.now() + timedelta(days=1)
        Post.objects.create(
            user=self.user, content='Déjà programmé', platform='twitter',
            status='scheduled', scheduled_at=slot,
        )
        post = Post.objects.create(user=self.user, content='Nouveau', platform='linkedin')
        nearby = (slot + timedelta(minutes=10)).isoformat()

        response = self.client.patch(f'/posts/{post.id}/schedule/', {'scheduled_at': nearby}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'scheduled')

    def test_schedule_force_conflict_bypasses_warning(self):
        slot = timezone.now() + timedelta(days=1)
        Post.objects.create(
            user=self.user, content='Déjà programmé', platform='linkedin',
            status='scheduled', scheduled_at=slot,
        )
        post = Post.objects.create(user=self.user, content='Nouveau', platform='linkedin')
        nearby = (slot + timedelta(minutes=20)).isoformat()

        response = self.client.patch(
            f'/posts/{post.id}/schedule/',
            {'scheduled_at': nearby, 'force_conflict': True},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'scheduled')

    def test_reschedule_rejected_when_current_slot_less_than_1h_away(self):
        post = Post.objects.create(
            user=self.user, content='Trop tard pour modifier', platform='linkedin',
            status='scheduled', scheduled_at=timezone.now() + timedelta(minutes=30),
        )
        new_slot = (timezone.now() + timedelta(days=3)).isoformat()

        response = self.client.patch(f'/posts/{post.id}/schedule/', {'scheduled_at': new_slot}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        post.refresh_from_db()
        self.assertNotEqual(post.scheduled_at.isoformat(), new_slot)

    def test_reschedule_allowed_when_current_slot_more_than_1h_away(self):
        post = Post.objects.create(
            user=self.user, content='Encore le temps', platform='linkedin',
            status='scheduled', scheduled_at=timezone.now() + timedelta(hours=2),
        )
        new_slot = (timezone.now() + timedelta(days=3)).isoformat()

        response = self.client.patch(f'/posts/{post.id}/schedule/', {'scheduled_at': new_slot}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_first_time_scheduling_a_draft_is_not_subject_to_1h_rule(self):
        post = Post.objects.create(user=self.user, content='Jamais programmé', platform='linkedin', status='draft')
        new_slot = (timezone.now() + timedelta(minutes=45)).isoformat()

        response = self.client.patch(f'/posts/{post.id}/schedule/', {'scheduled_at': new_slot}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)


@override_settings(LINKEDIN_CLIENT_ID='mock')
class LinkedInOAuthTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='liuser', password='pass')

    def _get_access_token(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        return str(RefreshToken.for_user(self.user).access_token)

    def test_auth_redirects_with_state_for_valid_token(self):
        token = self._get_access_token()
        response = self.client.get(f'/posts/linkedin/auth/?token={token}')
        self.assertEqual(response.status_code, 302)
        qs = parse_qs(urlparse(response.url).query)
        self.assertIn('state', qs)
        self.assertEqual(qs['code'][0], 'mock')

    def test_auth_rejects_invalid_token(self):
        response = self.client.get('/posts/linkedin/auth/?token=garbage')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_callback_full_mock_flow_creates_token(self):
        token = self._get_access_token()
        auth_response = self.client.get(f'/posts/linkedin/auth/?token={token}')
        qs = parse_qs(urlparse(auth_response.url).query)
        state, code = qs['state'][0], qs['code'][0]

        callback_response = self.client.get(f'/posts/linkedin/callback/?code={code}&state={state}')

        self.assertEqual(callback_response.status_code, 302)
        self.assertIn('linkedin=connected', callback_response.url)
        li_token = LinkedInToken.objects.get(user=self.user)
        self.assertEqual(decrypt(li_token.access_token), 'mock_access_token_klark_123')

    def test_callback_rejects_forged_state_never_issued(self):
        forged_state = f'{self.user.id}:not-a-real-nonce'
        response = self.client.get(f'/posts/linkedin/callback/?code=mock&state={forged_state}')

        self.assertEqual(response.status_code, 302)
        self.assertIn('linkedin=error', response.url)
        self.assertFalse(LinkedInToken.objects.filter(user=self.user).exists())

    def test_callback_rejects_reused_state(self):
        token = self._get_access_token()
        auth_response = self.client.get(f'/posts/linkedin/auth/?token={token}')
        qs = parse_qs(urlparse(auth_response.url).query)
        state, code = qs['state'][0], qs['code'][0]

        self.client.get(f'/posts/linkedin/callback/?code={code}&state={state}')
        second = self.client.get(f'/posts/linkedin/callback/?code={code}&state={state}')

        self.assertIn('linkedin=error', second.url)

    def test_disconnect_deletes_token(self):
        LinkedInToken.objects.create(
            user=self.user, access_token='enc', token_type='Bearer',
            expires_at=timezone.now() + timedelta(days=1),
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.delete('/posts/linkedin/disconnect/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(LinkedInToken.objects.filter(user=self.user).exists())

    def test_status_reports_connected(self):
        LinkedInToken.objects.create(
            user=self.user, access_token='enc', token_type='Bearer',
            expires_at=timezone.now() + timedelta(days=1),
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/posts/linkedin/status/')

        self.assertTrue(response.data['connected'])
