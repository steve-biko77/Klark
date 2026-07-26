from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone

from .encryption import encrypt, decrypt
from .models import LinkedInToken, Post
from .tasks import publish_post_task


class PublishPostTaskMockModeTest(TestCase):
    """LINKEDIN_CLIENT_ID='mock' est la valeur par défaut des settings de dev
    (cf. LinkedInAuthView/LinkedInCallbackView) — la tâche doit se comporter
    de façon cohérente : publication simulée, sans appel réseau réel."""

    def setUp(self):
        self.user = User.objects.create_user(username='taskuser', password='pass')
        LinkedInToken.objects.create(
            user=self.user, access_token=encrypt('mock_access_token_klark_123'),
            token_type='Bearer', expires_at=timezone.now() + timedelta(days=30),
        )
        self.post = Post.objects.create(
            user=self.user, content='Post à publier', platform='linkedin',
            status='scheduled', scheduled_at=timezone.now(),
        )

    def test_publishes_post_in_mock_mode(self):
        result = publish_post_task.apply(args=[self.post.id]).get()

        self.post.refresh_from_db()
        self.assertEqual(self.post.status, 'published')
        self.assertIsNotNone(self.post.published_at)
        self.assertTrue(self.post.post_urn)
        self.assertEqual(result['status'], 'published')

    def test_skips_post_not_in_scheduled_status(self):
        self.post.status = 'draft'
        self.post.save()

        result = publish_post_task.apply(args=[self.post.id]).get()

        self.assertEqual(result['status'], 'skipped')
        self.post.refresh_from_db()
        self.assertEqual(self.post.status, 'draft')

    def test_fails_without_linkedin_token(self):
        self.user.linkedin_token.delete()

        result = publish_post_task.apply(args=[self.post.id]).get()

        self.assertEqual(result['status'], 'failed')
        self.post.refresh_from_db()
        self.assertEqual(self.post.status, 'failed')

    def test_skips_deleted_post_cleanly(self):
        post_id = self.post.id
        self.post.delete()

        result = publish_post_task.apply(args=[post_id]).get()

        self.assertEqual(result['status'], 'skipped')


class PublishPostTaskRealModeTest(TestCase):
    """LINKEDIN_CLIENT_ID != 'mock' — la tâche doit suivre le flow réel décrit
    dans le prompt technique (decrypt -> check expiry -> refresh -> publish)."""

    def setUp(self):
        self.user = User.objects.create_user(username='realtaskuser', password='pass')
        self.post = Post.objects.create(
            user=self.user, content='Post réel', platform='linkedin',
            status='scheduled', scheduled_at=timezone.now(),
        )

    @override_settings(LINKEDIN_CLIENT_ID='real_client_id')
    @patch('apps.posts.tasks._call_linkedin_api')
    def test_publishes_via_real_api_and_stores_urn(self, mock_call_api):
        LinkedInToken.objects.create(
            user=self.user, access_token=encrypt('real_access_token'),
            token_type='Bearer', expires_at=timezone.now() + timedelta(days=30),
        )
        mock_call_api.side_effect = [
            {'id': 'abc123'},  # GET /v2/me
            ('urn:li:share:999', 201),  # POST /v2/ugcPosts -> (post_urn, status_code)
        ]

        result = publish_post_task.apply(args=[self.post.id]).get()

        self.post.refresh_from_db()
        self.assertEqual(self.post.status, 'published')
        self.assertEqual(self.post.post_urn, 'urn:li:share:999')
        self.assertEqual(result['status'], 'published')

    @override_settings(LINKEDIN_CLIENT_ID='real_client_id')
    @patch('apps.posts.tasks._refresh_linkedin_token')
    @patch('apps.posts.tasks._call_linkedin_api')
    def test_refreshes_expired_token_before_publishing(self, mock_call_api, mock_refresh):
        LinkedInToken.objects.create(
            user=self.user, access_token=encrypt('stale_token'), token_type='Bearer',
            expires_at=timezone.now() - timedelta(hours=1),
            refresh_token=encrypt('refresh_token_value'),
        )
        mock_refresh.return_value = 'fresh_access_token'
        mock_call_api.side_effect = [{'id': 'abc123'}, ('urn:li:share:1', 201)]

        result = publish_post_task.apply(args=[self.post.id]).get()

        mock_refresh.assert_called_once()
        self.assertEqual(result['status'], 'published')
        self.assertEqual(mock_call_api.call_args_list[0].args[0], 'fresh_access_token')

    def test_refresh_linkedin_token_persists_new_encrypted_token(self):
        from apps.posts.tasks import _refresh_linkedin_token

        token = LinkedInToken.objects.create(
            user=self.user, access_token=encrypt('stale_token'), token_type='Bearer',
            expires_at=timezone.now() - timedelta(hours=1),
            refresh_token=encrypt('refresh_token_value'),
        )
        with patch('apps.posts.tasks.urllib.request.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"access_token": "fresh_access_token", "expires_in": 5184000}'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            new_token = _refresh_linkedin_token(token)

        self.assertEqual(new_token, 'fresh_access_token')
        token.refresh_from_db()
        self.assertEqual(decrypt(token.access_token), 'fresh_access_token')

    @override_settings(LINKEDIN_CLIENT_ID='real_client_id')
    @patch('apps.posts.tasks._refresh_linkedin_token')
    def test_failed_refresh_marks_post_failed(self, mock_refresh):
        LinkedInToken.objects.create(
            user=self.user, access_token=encrypt('stale_token'), token_type='Bearer',
            expires_at=timezone.now() - timedelta(hours=1),
            refresh_token=encrypt('refresh_token_value'),
        )
        mock_refresh.return_value = None

        result = publish_post_task.apply(args=[self.post.id]).get()

        self.assertEqual(result['status'], 'failed')
        self.post.refresh_from_db()
        self.assertEqual(self.post.status, 'failed')

    @override_settings(LINKEDIN_CLIENT_ID='real_client_id')
    @patch('apps.posts.tasks._call_linkedin_api')
    def test_non_201_response_marks_post_failed(self, mock_call_api):
        LinkedInToken.objects.create(
            user=self.user, access_token=encrypt('real_access_token'),
            token_type='Bearer', expires_at=timezone.now() + timedelta(days=30),
        )
        mock_call_api.side_effect = [{'id': 'abc123'}, (None, 400)]

        result = publish_post_task.apply(args=[self.post.id]).get()

        self.assertEqual(result['status'], 'failed')
        self.post.refresh_from_db()
        self.assertEqual(self.post.status, 'failed')

    @override_settings(LINKEDIN_CLIENT_ID='real_client_id')
    @patch('apps.posts.tasks._call_linkedin_api')
    def test_rate_limit_retries_with_backoff_then_fails_after_max_retries(self, mock_call_api):
        LinkedInToken.objects.create(
            user=self.user, access_token=encrypt('real_access_token'),
            token_type='Bearer', expires_at=timezone.now() + timedelta(days=30),
        )
        mock_call_api.side_effect = [
            {'id': 'abc123'}, (None, 429),
            {'id': 'abc123'}, (None, 429),
            {'id': 'abc123'}, (None, 429),
            {'id': 'abc123'}, (None, 429),
        ]

        publish_post_task.apply(args=[self.post.id]).get(propagate=False)

        self.post.refresh_from_db()
        self.assertEqual(self.post.status, 'failed')
