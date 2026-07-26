from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status

from apps.authentication.models import Profile
from apps.sources.models import Source
from .models import Article, DailyBriefing
from .services import (
    build_digest_email_html, maybe_send_daily_digest,
    make_unsubscribe_token, verify_unsubscribe_token,
)


class UnsubscribeTokenTest(TestCase):

    def test_roundtrip(self):
        token = make_unsubscribe_token(42)
        self.assertEqual(verify_unsubscribe_token(token), 42)

    def test_garbage_token_returns_none(self):
        self.assertIsNone(verify_unsubscribe_token('not-a-real-token'))


class BuildDigestEmailHtmlTest(TestCase):

    def test_includes_signal_titles_and_lines(self):
        signals = [{'article_id': 1, 'article_title': 'Titre du signal', 'lines': ['L1', 'L2', 'L3']}]
        html = build_digest_email_html(signals, unsubscribe_url='https://klark.app/unsub')
        self.assertIn('Titre du signal', html)
        self.assertIn('L1', html)
        self.assertIn('https://klark.app/unsub', html)

    def test_shows_message_when_no_signals(self):
        html = build_digest_email_html([], unsubscribe_url='https://klark.app/unsub')
        self.assertIn('actualités', html.lower())


class MaybeSendDailyDigestTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='digestuser', password='pass', email='digest@example.com')
        self.source = Source.objects.create(user=self.user, url='https://example.com/rss')

    @patch('apps.articles.services.anthropic.Anthropic')
    def test_sends_email_when_digest_enabled(self, mock_anthropic_cls):
        from unittest.mock import MagicMock
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text='Ligne 1.\nLigne 2.\nLigne 3.')]
        mock_message.usage.input_tokens = 10
        mock_message.usage.output_tokens = 5
        mock_anthropic_cls.return_value.messages.create.return_value = mock_message

        Profile.objects.create(user=self.user, persona='TRADER', tone='DIRECT', email_digest=True)
        Article.objects.create(
            source=self.source, title='Signal', content='...', url='https://a.com/1', score=90,
        )

        sent = maybe_send_daily_digest(self.user)

        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('digest@example.com', mail.outbox[0].to)
        self.assertIn('1 signal', mail.outbox[0].subject)

    def test_does_not_send_when_digest_disabled(self):
        Profile.objects.create(user=self.user, persona='TRADER', tone='DIRECT', email_digest=False)

        sent = maybe_send_daily_digest(self.user)

        self.assertFalse(sent)
        self.assertEqual(len(mail.outbox), 0)

    def test_does_not_send_without_profile(self):
        sent = maybe_send_daily_digest(self.user)
        self.assertFalse(sent)
        self.assertEqual(len(mail.outbox), 0)

    def test_reuses_existing_briefing_for_the_day(self):
        Profile.objects.create(user=self.user, persona='TRADER', tone='DIRECT', email_digest=True)
        briefing = DailyBriefing.objects.create(user=self.user, date=__import__('django.utils.timezone', fromlist=['now']).now().date(), content=[])

        maybe_send_daily_digest(self.user)

        self.assertEqual(DailyBriefing.objects.filter(user=self.user).count(), 1)
        self.assertEqual(DailyBriefing.objects.get(user=self.user).id, briefing.id)


class UnsubscribeViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='unsubuser', password='pass')
        self.profile = Profile.objects.create(user=self.user, persona='TRADER', tone='DIRECT', email_digest=True)

    def test_unsubscribe_disables_digest(self):
        token = make_unsubscribe_token(self.user.id)
        response = self.client.get(f'/briefings/unsubscribe/?token={token}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.email_digest)

    def test_invalid_token_returns_400(self):
        response = self.client.get('/briefings/unsubscribe/?token=garbage')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
