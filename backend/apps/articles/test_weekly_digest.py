from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from apps.authentication.models import Profile
from apps.posts.models import Analytics, Post
from .services import (
    gather_weekly_stats, maybe_send_weekly_digest,
    make_weekly_unsubscribe_token, verify_weekly_unsubscribe_token,
)


def _mock_anthropic(mock_anthropic_cls, text='Publiez le mardi, vos posts y performent 2x mieux.'):
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=text)]
    mock_message.usage.input_tokens = 15
    mock_message.usage.output_tokens = 10
    mock_anthropic_cls.return_value.messages.create.return_value = mock_message


class WeeklyUnsubscribeTokenTest(TestCase):

    def test_roundtrip(self):
        token = make_weekly_unsubscribe_token(7)
        self.assertEqual(verify_weekly_unsubscribe_token(token), 7)

    def test_garbage_token_returns_none(self):
        self.assertIsNone(verify_weekly_unsubscribe_token('garbage'))

    def test_daily_and_weekly_tokens_are_not_interchangeable(self):
        from apps.articles.services import make_unsubscribe_token, verify_unsubscribe_token
        daily_token = make_unsubscribe_token(9)
        self.assertIsNone(verify_weekly_unsubscribe_token(daily_token))


class GatherWeeklyStatsTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='weeklystats', password='pass')

    def _last_monday_at(self, hour=10):
        from apps.posts.services import USER_TIMEZONE
        now_local = timezone.localtime(timezone.now(), USER_TIMEZONE)
        this_monday = now_local.date() - timedelta(days=now_local.weekday())
        last_monday = this_monday - timedelta(days=7)
        naive = timezone.datetime.combine(last_monday, timezone.datetime.min.time().replace(hour=hour))
        return naive.replace(tzinfo=USER_TIMEZONE)

    def test_no_activity_gives_zeroed_stats(self):
        stats = gather_weekly_stats(self.user)
        self.assertEqual(stats['posts_generated'], 0)
        self.assertEqual(stats['posts_published'], 0)
        self.assertIsNone(stats['best_post'])

    def test_counts_posts_published_last_week_only(self):
        Post.objects.create(
            user=self.user, content='Semaine dernière', platform='linkedin',
            status='published', published_at=self._last_monday_at(),
        )
        Post.objects.create(
            user=self.user, content='Trop vieux', platform='linkedin',
            status='published', published_at=self._last_monday_at() - timedelta(days=14),
        )
        stats = gather_weekly_stats(self.user)
        self.assertEqual(stats['posts_published'], 1)

    def test_best_post_is_highest_engagement_of_the_week(self):
        low = Post.objects.create(
            user=self.user, content='Post faible', platform='linkedin',
            status='published', published_at=self._last_monday_at(),
        )
        high = Post.objects.create(
            user=self.user, content='Post fort', platform='linkedin',
            status='published', published_at=self._last_monday_at(hour=14),
        )
        Analytics.objects.create(post=low, likes=1, views=100, shares=0, comments=0, engagement_rate=1.0)
        Analytics.objects.create(post=high, likes=50, views=100, shares=10, comments=10, engagement_rate=70.0)

        stats = gather_weekly_stats(self.user)

        self.assertEqual(stats['best_post']['engagement_rate'], 70.0)

    def test_includes_streak_and_influence_score_from_profile(self):
        Profile.objects.create(
            user=self.user, persona='CREATEUR', tone='EXPERT',
            streak_current=5, influence_score=300, influence_score_previous=250,
        )
        stats = gather_weekly_stats(self.user)
        self.assertEqual(stats['streak_current'], 5)
        self.assertEqual(stats['influence_score_trend'], 50)


class MaybeSendWeeklyDigestTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='weeklysend', password='pass', email='weekly@example.com',
        )

    @patch('apps.articles.services.anthropic.Anthropic')
    def test_sends_when_weekly_digest_enabled(self, mock_anthropic_cls):
        _mock_anthropic(mock_anthropic_cls)
        Profile.objects.create(user=self.user, persona='CREATEUR', tone='EXPERT', weekly_digest=True)

        sent = maybe_send_weekly_digest(self.user)

        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('weekly@example.com', mail.outbox[0].to)

    def test_does_not_send_when_disabled(self):
        Profile.objects.create(user=self.user, persona='CREATEUR', tone='EXPERT', weekly_digest=False)

        sent = maybe_send_weekly_digest(self.user)

        self.assertFalse(sent)
        self.assertEqual(len(mail.outbox), 0)

    def test_does_not_send_without_profile(self):
        sent = maybe_send_weekly_digest(self.user)
        self.assertFalse(sent)

    @patch('apps.articles.services.anthropic.Anthropic')
    def test_encouragement_when_no_posts_published(self, mock_anthropic_cls):
        _mock_anthropic(mock_anthropic_cls, text='Publiez votre premier post cette semaine pour démarrer !')
        Profile.objects.create(user=self.user, persona='CREATEUR', tone='EXPERT', weekly_digest=True)

        sent = maybe_send_weekly_digest(self.user)

        self.assertTrue(sent)
        self.assertIn('Aucun post publié cette semaine', mail.outbox[0].alternatives[0][0])


class SendWeeklyDigestViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='sendview', password='pass', email='send@example.com')
        self.client.force_authenticate(user=self.user)

    def test_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.post('/briefings/send-weekly-digest/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('apps.articles.views.maybe_send_weekly_digest')
    def test_calls_service_and_returns_sent_flag(self, mock_send):
        mock_send.return_value = True
        response = self.client.post('/briefings/send-weekly-digest/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['sent'])


class UnsubscribeWeeklyDigestViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='unsubweekly', password='pass')
        self.profile = Profile.objects.create(
            user=self.user, persona='CREATEUR', tone='EXPERT', weekly_digest=True,
        )

    def test_unsubscribe_disables_weekly_digest_only(self):
        token = make_weekly_unsubscribe_token(self.user.id)
        response = self.client.get(f'/briefings/unsubscribe-weekly/?token={token}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.weekly_digest)
        self.assertTrue(self.profile.email_digest)

    def test_invalid_token_returns_400(self):
        response = self.client.get('/briefings/unsubscribe-weekly/?token=garbage')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
