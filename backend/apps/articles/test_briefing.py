from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from apps.authentication.models import Profile
from apps.sources.models import Source
from .models import Article, DailyBriefing
from .services import generate_daily_briefing


def _mock_anthropic_client(text='Signal clé.\nSource fiable.\nImplication marché.'):
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=text)]
    mock_message.usage.input_tokens = 50
    mock_message.usage.output_tokens = 20
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message
    return mock_client


class GenerateDailyBriefingServiceTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='trader1', password='pass')
        Profile.objects.create(user=self.user, persona='TRADER', tone='DIRECT')
        self.source = Source.objects.create(user=self.user, url='https://example.com/rss')

    @patch('apps.articles.services.anthropic.Anthropic')
    def test_selects_up_to_5_articles_score_above_70_last_24h(self, mock_anthropic_cls):
        mock_anthropic_cls.return_value = _mock_anthropic_client()

        for i in range(7):
            Article.objects.create(
                source=self.source, title=f'Article {i}', content='...',
                url=f'https://a.com/{i}', score=80 - i,
            )
        # article trop vieux, hors fenêtre 24h
        old = Article.objects.create(
            source=self.source, title='Vieux', content='...', url='https://a.com/old', score=99,
        )
        Article.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=2))
        # score trop bas
        Article.objects.create(
            source=self.source, title='Pas pertinent', content='...', url='https://a.com/low', score=50,
        )

        briefing = generate_daily_briefing(self.user)

        self.assertEqual(len(briefing.content), 5)
        titles = [s['article_title'] for s in briefing.content]
        self.assertNotIn('Vieux', titles)
        self.assertNotIn('Pas pertinent', titles)

    @patch('apps.articles.services.anthropic.Anthropic')
    def test_each_signal_has_exactly_3_lines(self, mock_anthropic_cls):
        mock_anthropic_cls.return_value = _mock_anthropic_client()
        Article.objects.create(
            source=self.source, title='Signal', content='...', url='https://a.com/1', score=90,
        )

        briefing = generate_daily_briefing(self.user)

        self.assertEqual(len(briefing.content[0]['lines']), 3)

    @patch('apps.articles.services.anthropic.Anthropic')
    def test_returns_existing_briefing_if_already_generated_today(self, mock_anthropic_cls):
        mock_anthropic_cls.return_value = _mock_anthropic_client()
        Article.objects.create(
            source=self.source, title='Signal', content='...', url='https://a.com/1', score=90,
        )

        first = generate_daily_briefing(self.user)
        second = generate_daily_briefing(self.user)

        self.assertEqual(first.id, second.id)
        mock_anthropic_cls.return_value.messages.create.assert_called_once()

    @patch('apps.articles.services.anthropic.Anthropic')
    def test_no_relevant_articles_creates_empty_briefing(self, mock_anthropic_cls):
        mock_anthropic_cls.return_value = _mock_anthropic_client()

        briefing = generate_daily_briefing(self.user)

        self.assertEqual(briefing.content, [])


class BriefingEndpointTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='trader2', password='pass')
        self.client.force_authenticate(user=self.user)
        self.source = Source.objects.create(user=self.user, url='https://example.com/rss')

    @patch('apps.articles.services.anthropic.Anthropic')
    def test_today_briefing_generated_lazily_for_trader(self, mock_anthropic_cls):
        mock_anthropic_cls.return_value = _mock_anthropic_client()
        Profile.objects.create(user=self.user, persona='TRADER', tone='DIRECT')
        Article.objects.create(
            source=self.source, title='Signal', content='...', url='https://a.com/1', score=90,
        )

        response = self.client.get('/briefings/today/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['content']), 1)

    def test_non_trader_gets_empty_response(self):
        Profile.objects.create(user=self.user, persona='CREATEUR', tone='EXPERT')

        response = self.client.get('/briefings/today/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data)

    def test_no_profile_gets_empty_response(self):
        response = self.client.get('/briefings/today/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data)

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/briefings/today/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
