from datetime import timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from apps.authentication.models import Profile
from .models import Analytics, Post
from .services import (
    calculate_streak, should_remind_publish_today, update_streak,
    calculate_influence_score, maybe_update_influence_score,
)

PARIS = ZoneInfo('Europe/Paris')


def _published_at(days_ago: int):
    """Un datetime aware, à midi Paris, il y a `days_ago` jours."""
    local_now = timezone.localtime(timezone.now(), PARIS)
    target_date = local_now.date() - timedelta(days=days_ago)
    naive_noon = timezone.datetime.combine(target_date, timezone.datetime.min.time().replace(hour=12))
    return naive_noon.replace(tzinfo=PARIS)


class CalculateStreakTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='streakuser', password='pass')

    def test_no_published_posts_returns_zero(self):
        self.assertEqual(calculate_streak(self.user), 0)

    def test_published_today_only_gives_streak_one(self):
        Post.objects.create(
            user=self.user, content='Post', platform='linkedin',
            status='published', published_at=_published_at(0),
        )
        self.assertEqual(calculate_streak(self.user), 1)

    def test_three_consecutive_days_gives_streak_three(self):
        for days_ago in (0, 1, 2):
            Post.objects.create(
                user=self.user, content=f'Post J-{days_ago}', platform='linkedin',
                status='published', published_at=_published_at(days_ago),
            )
        self.assertEqual(calculate_streak(self.user), 3)

    def test_gap_breaks_streak(self):
        Post.objects.create(
            user=self.user, content='Aujourd\'hui', platform='linkedin',
            status='published', published_at=_published_at(0),
        )
        Post.objects.create(
            user=self.user, content='Il y a 3 jours', platform='linkedin',
            status='published', published_at=_published_at(3),
        )
        self.assertEqual(calculate_streak(self.user), 1)

    def test_nothing_today_or_yesterday_resets_to_zero(self):
        Post.objects.create(
            user=self.user, content='Il y a 2 jours', platform='linkedin',
            status='published', published_at=_published_at(2),
        )
        self.assertEqual(calculate_streak(self.user), 0)

    def test_last_post_yesterday_still_counts_streak(self):
        Post.objects.create(
            user=self.user, content='Hier', platform='linkedin',
            status='published', published_at=_published_at(1),
        )
        Post.objects.create(
            user=self.user, content='Avant-hier', platform='linkedin',
            status='published', published_at=_published_at(2),
        )
        self.assertEqual(calculate_streak(self.user), 2)

    def test_draft_posts_do_not_count(self):
        Post.objects.create(
            user=self.user, content='Brouillon', platform='linkedin',
            status='draft', published_at=_published_at(0),
        )
        self.assertEqual(calculate_streak(self.user), 0)


class ShouldRemindPublishTodayTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='reminduser', password='pass')

    def test_true_when_last_post_yesterday(self):
        Post.objects.create(
            user=self.user, content='Hier', platform='linkedin',
            status='published', published_at=_published_at(1),
        )
        self.assertTrue(should_remind_publish_today(self.user))

    def test_false_when_already_published_today(self):
        Post.objects.create(
            user=self.user, content='Hier', platform='linkedin',
            status='published', published_at=_published_at(1),
        )
        Post.objects.create(
            user=self.user, content='Aujourd\'hui', platform='linkedin',
            status='published', published_at=_published_at(0),
        )
        self.assertFalse(should_remind_publish_today(self.user))

    def test_false_when_no_posts_at_all(self):
        self.assertFalse(should_remind_publish_today(self.user))


class UpdateStreakTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='updateuser', password='pass')

    def test_creates_profile_and_sets_streak_current(self):
        Post.objects.create(
            user=self.user, content='Post', platform='linkedin',
            status='published', published_at=_published_at(0),
        )
        profile = update_streak(self.user)
        self.assertEqual(profile.streak_current, 1)
        self.assertEqual(profile.streak_max, 1)

    def test_streak_max_never_decreases(self):
        profile = Profile.objects.create(
            user=self.user, persona='CREATEUR', tone='EXPERT', streak_max=10, streak_current=10,
        )
        # Rien publié aujourd'hui ni hier -> streak_current retombe à 0
        update_streak(self.user)
        profile.refresh_from_db()
        self.assertEqual(profile.streak_current, 0)
        self.assertEqual(profile.streak_max, 10)


class CalculateInfluenceScoreTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='scoreuser', password='pass')

    def test_zero_activity_gives_zero_score(self):
        self.assertEqual(calculate_influence_score(self.user), 0)

    def test_score_is_bounded_at_1000_when_everything_maxed(self):
        # 35 jours consécutifs publiés (dont les 30 derniers) + engagement 100% partout
        # -> les 3 composantes (posts/30j, engagement, streak) sont toutes plafonnées.
        for i in range(35):
            post = Post.objects.create(
                user=self.user, content=f'Post {i}', platform='linkedin',
                status='published', published_at=timezone.now() - timedelta(days=i),
            )
            Analytics.objects.create(post=post, likes=100, views=100, shares=100, comments=100, engagement_rate=100.0)

        score = calculate_influence_score(self.user)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1000)
        self.assertEqual(score, 1000)

    def test_more_activity_gives_higher_score(self):
        low_user = User.objects.create_user(username='lowactivity', password='pass')
        post = Post.objects.create(
            user=low_user, content='Un seul post', platform='linkedin',
            status='published', published_at=timezone.now(),
        )
        Analytics.objects.create(post=post, likes=1, views=100, shares=0, comments=0, engagement_rate=1.0)

        for i in range(10):
            post = Post.objects.create(
                user=self.user, content=f'Post {i}', platform='linkedin',
                status='published', published_at=timezone.now() - timedelta(days=i),
            )
            Analytics.objects.create(post=post, likes=20, views=100, shares=5, comments=5, engagement_rate=30.0)

        self.assertGreater(calculate_influence_score(self.user), calculate_influence_score(low_user))


class MaybeUpdateInfluenceScoreTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='lazyupdate', password='pass')

    def test_first_call_sets_score_and_timestamp(self):
        profile = maybe_update_influence_score(self.user)
        self.assertIsNotNone(profile.influence_score_updated_at)

    def test_recent_update_is_not_recomputed(self):
        Profile.objects.create(
            user=self.user, persona='CREATEUR', tone='EXPERT',
            influence_score=500, influence_score_updated_at=timezone.now(),
        )
        Post.objects.create(
            user=self.user, content='Nouveau post', platform='linkedin',
            status='published', published_at=timezone.now(),
        )
        Analytics.objects.create(
            post=Post.objects.first(), likes=100, views=100, shares=100, comments=100, engagement_rate=100.0,
        )

        profile = maybe_update_influence_score(self.user)

        self.assertEqual(profile.influence_score, 500)

    def test_stale_update_is_recomputed_and_tracks_previous(self):
        Profile.objects.create(
            user=self.user, persona='CREATEUR', tone='EXPERT',
            influence_score=100, influence_score_updated_at=timezone.now() - timedelta(days=8),
        )

        profile = maybe_update_influence_score(self.user)

        self.assertEqual(profile.influence_score_previous, 100)


class GamificationViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='gamifyview', password='pass')
        self.client.force_authenticate(user=self.user)

    def test_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/gamification/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_expected_shape(self):
        response = self.client.get('/gamification/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in (
            'streak_current', 'streak_max', 'influence_score',
            'influence_score_trend', 'remind_publish_today',
        ):
            self.assertIn(key, response.data)

    def test_remind_flag_true_when_last_post_yesterday(self):
        Post.objects.create(
            user=self.user, content='Hier', platform='linkedin',
            status='published', published_at=_published_at(1),
        )
        response = self.client.get('/gamification/')
        self.assertTrue(response.data['remind_publish_today'])
