import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from .encryption import encrypt
from .models import Analytics, LinkedInToken, Post
from .services import collect_post_analytics, collect_analytics_for_user, get_analytics_overview


class CollectPostAnalyticsTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='analyticsuser', password='pass')
        self.post = Post.objects.create(
            user=self.user, content='Mon post publié', platform='linkedin',
            status='published', post_urn='urn:li:share:123', published_at=timezone.now(),
        )
        LinkedInToken.objects.create(
            user=self.user, access_token=encrypt('real_token'), token_type='Bearer',
            expires_at=timezone.now() + timedelta(days=30),
        )

    def test_returns_none_without_post_urn(self):
        self.post.post_urn = None
        self.post.save()
        self.assertIsNone(collect_post_analytics(self.post))

    def test_returns_none_without_linkedin_token(self):
        self.user.linkedin_token.delete()
        self.assertIsNone(collect_post_analytics(self.post))

    @patch('apps.posts.services._fetch_linkedin_metrics')
    def test_creates_analytics_row_with_computed_engagement_rate(self, mock_fetch):
        mock_fetch.return_value = {'likes': 10, 'views': 200, 'shares': 5, 'comments': 5}

        analytics = collect_post_analytics(self.post)

        self.assertIsNotNone(analytics)
        self.assertEqual(analytics.likes, 10)
        self.assertEqual(analytics.views, 200)
        # (10 + 5 + 5) / 200 * 100 = 10.0
        self.assertEqual(analytics.engagement_rate, 10.0)

    @patch('apps.posts.services._fetch_linkedin_metrics')
    def test_zero_views_gives_zero_engagement_rate_no_crash(self, mock_fetch):
        mock_fetch.return_value = {'likes': 3, 'views': 0, 'shares': 0, 'comments': 0}

        analytics = collect_post_analytics(self.post)

        self.assertEqual(analytics.engagement_rate, 0.0)

    @patch('apps.posts.services._fetch_linkedin_metrics')
    def test_api_failure_degrades_gracefully(self, mock_fetch):
        mock_fetch.side_effect = Exception('LinkedIn API indisponible')

        result = collect_post_analytics(self.post)

        self.assertIsNone(result)
        self.assertEqual(Analytics.objects.filter(post=self.post).count(), 0)


class CollectAnalyticsForUserTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='bulkuser', password='pass')
        LinkedInToken.objects.create(
            user=self.user, access_token=encrypt('real_token'), token_type='Bearer',
            expires_at=timezone.now() + timedelta(days=30),
        )

    @patch('apps.posts.services._fetch_linkedin_metrics')
    def test_collects_only_published_posts_with_urn(self, mock_fetch):
        mock_fetch.return_value = {'likes': 1, 'views': 10, 'shares': 0, 'comments': 0}
        Post.objects.create(
            user=self.user, content='Publié avec urn', platform='linkedin',
            status='published', post_urn='urn:li:share:1', published_at=timezone.now(),
        )
        Post.objects.create(
            user=self.user, content='Publié sans urn', platform='linkedin', status='published',
        )
        Post.objects.create(user=self.user, content='Brouillon', platform='linkedin', status='draft')

        collected = collect_analytics_for_user(self.user)

        self.assertEqual(collected, 1)
        self.assertEqual(Analytics.objects.filter(post__user=self.user).count(), 1)

    @patch('apps.posts.services._fetch_linkedin_metrics')
    def test_one_failure_does_not_block_others(self, mock_fetch):
        mock_fetch.side_effect = [Exception('boom'), {'likes': 1, 'views': 10, 'shares': 0, 'comments': 0}]
        Post.objects.create(
            user=self.user, content='Échoue', platform='linkedin',
            status='published', post_urn='urn:li:share:fail', published_at=timezone.now(),
        )
        Post.objects.create(
            user=self.user, content='Réussit', platform='linkedin',
            status='published', post_urn='urn:li:share:ok', published_at=timezone.now(),
        )

        collected = collect_analytics_for_user(self.user)

        self.assertEqual(collected, 1)


class AnalyticsOverviewServiceTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='overviewuser', password='pass')

    def test_no_data_returns_empty_but_valid_shape(self):
        overview = get_analytics_overview(self.user)
        self.assertEqual(overview['evolution_30j'], [])
        self.assertEqual(overview['total_views'], 0)
        self.assertIsNone(overview['best_post'])
        self.assertEqual(overview['posts'], [])

    def test_published_post_without_analytics_marked_unavailable(self):
        Post.objects.create(
            user=self.user, content='Publié, pas encore collecté', platform='linkedin',
            status='published', published_at=timezone.now(),
        )
        overview = get_analytics_overview(self.user)
        self.assertEqual(len(overview['posts']), 1)
        self.assertFalse(overview['posts'][0]['analytics_available'])
        self.assertIsNone(overview['posts'][0]['engagement_rate'])

    def test_best_post_and_platform_and_above_average_flag(self):
        low_post = Post.objects.create(
            user=self.user, content='Post moyen', platform='linkedin',
            status='published', published_at=timezone.now(),
        )
        high_post = Post.objects.create(
            user=self.user, content='Post excellent', platform='twitter',
            status='published', published_at=timezone.now(),
        )
        Analytics.objects.create(post=low_post, likes=1, views=100, shares=0, comments=0, engagement_rate=1.0)
        Analytics.objects.create(post=high_post, likes=50, views=100, shares=10, comments=10, engagement_rate=70.0)

        overview = get_analytics_overview(self.user)

        self.assertEqual(overview['best_post']['post_id'], high_post.id)
        self.assertEqual(overview['best_platform'], 'twitter')
        self.assertEqual(overview['total_views'], 200)

        by_id = {p['post_id']: p for p in overview['posts']}
        self.assertTrue(by_id[high_post.id]['above_average'])
        self.assertFalse(by_id[low_post.id]['above_average'])


class AnalyticsViewsTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='endpointuser', password='pass')
        self.client.force_authenticate(user=self.user)

    def test_overview_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/analytics/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_overview_returns_200_with_empty_data(self):
        response = self.client.get('/analytics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('posts', response.data)

    @patch('apps.posts.views.collect_analytics_for_user')
    def test_collect_endpoint_calls_service(self, mock_collect):
        mock_collect.return_value = 3
        response = self.client.post('/analytics/collect/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['collected'], 3)
