from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from apps.authentication.models import Profile
from .models import Analytics, Post
from .services import update_style_memory, reset_style_prompt


def _mock_anthropic(mock_anthropic_cls, text='Vos posts commencent par une question percutante.'):
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=text)]
    mock_message.usage.input_tokens = 20
    mock_message.usage.output_tokens = 15
    mock_anthropic_cls.return_value.messages.create.return_value = mock_message
    return mock_message


class UpdateStyleMemoryTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='styleuser', password='pass')
        Profile.objects.create(user=self.user, persona='CREATEUR', tone='EXPERT', style_prompt='Ton direct.')

    def _create_published_with_analytics(self, n, base_rate=10.0):
        for i in range(n):
            post = Post.objects.create(
                user=self.user, content=f'Post {i}', platform='linkedin',
                status='published', published_at=timezone.now(),
            )
            Analytics.objects.create(
                post=post, likes=1, views=100, shares=0, comments=0, engagement_rate=base_rate + i,
            )

    def test_fewer_than_5_published_returns_none_and_does_not_touch_profile(self):
        self._create_published_with_analytics(3)
        original_prompt = self.user.profile.style_prompt

        result = update_style_memory(self.user)

        self.assertIsNone(result)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.style_prompt, original_prompt)

    @patch('apps.posts.services.anthropic.Anthropic')
    def test_appends_learned_text_without_replacing_existing_style(self, mock_anthropic_cls):
        _mock_anthropic(mock_anthropic_cls, text='Vos posts utilisent des séries de 3 éléments.')
        self._create_published_with_analytics(6)

        profile = update_style_memory(self.user)

        self.assertIn('Ton direct.', profile.style_prompt)
        self.assertIn('séries de 3 éléments', profile.style_prompt)

    @patch('apps.posts.services.anthropic.Anthropic')
    def test_records_style_history_entry(self, mock_anthropic_cls):
        _mock_anthropic(mock_anthropic_cls)
        self._create_published_with_analytics(6)

        profile = update_style_memory(self.user)

        self.assertEqual(len(profile.style_history), 1)
        self.assertEqual(profile.style_history[0]['posts_analyzed'], 6)

    @patch('apps.posts.services.anthropic.Anthropic')
    def test_selects_top_posts_by_engagement_rate(self, mock_anthropic_cls):
        _mock_anthropic(mock_anthropic_cls)
        self._create_published_with_analytics(12)

        update_style_memory(self.user)

        prompt_sent = mock_anthropic_cls.return_value.messages.create.call_args.kwargs['messages'][0]['content']
        # Les posts avec le meilleur engagement (rate = 10+i, i de 0 à 11) sont les 10 derniers.
        self.assertIn('Post 11', prompt_sent)
        self.assertNotIn('Post 0\n', prompt_sent)


class ResetStylePromptTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='resetuser', password='pass')

    def test_resets_to_manual_value(self):
        Profile.objects.create(
            user=self.user, persona='CREATEUR', tone='EXPERT',
            style_prompt='Manuel + appris automatiquement', style_prompt_manual='Manuel',
        )

        profile = reset_style_prompt(self.user)

        self.assertEqual(profile.style_prompt, 'Manuel')


class LearnStyleViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='learnview', password='pass')
        self.client.force_authenticate(user=self.user)

    def test_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.post('/profile/learn-style/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_not_enough_posts_returns_updated_false(self):
        response = self.client.post('/profile/learn-style/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['updated'])


class ResetStyleViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='resetview', password='pass')
        self.client.force_authenticate(user=self.user)

    def test_resets_style_prompt(self):
        Profile.objects.create(
            user=self.user, persona='CREATEUR', tone='EXPERT',
            style_prompt='Appris', style_prompt_manual='Manuel de base',
        )
        response = self.client.post('/profile/reset-style/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['style_prompt'], 'Manuel de base')


class ProfilePatchSyncsManualStyleTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='syncuser', password='pass')
        self.client.force_authenticate(user=self.user)

    def test_patching_style_prompt_updates_manual_baseline(self):
        response = self.client.patch('/profile/', {'style_prompt': 'Nouveau style saisi à la main'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.style_prompt_manual, 'Nouveau style saisi à la main')

    def test_patching_other_fields_does_not_touch_manual_baseline(self):
        Profile.objects.create(
            user=self.user, persona='CREATEUR', tone='EXPERT', style_prompt_manual='Original',
        )
        self.client.patch('/profile/', {'sector': 'Finance'}, format='json')

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.style_prompt_manual, 'Original')
