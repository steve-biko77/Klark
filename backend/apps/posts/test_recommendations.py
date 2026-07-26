from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Analytics, Post
from .services import compute_format_recommendations


def _make_published_post(user, content, days_ago, hour, engagement_rate):
    published_at = (timezone.now() - timedelta(days=days_ago)).replace(hour=hour, minute=0, second=0, microsecond=0)
    post = Post.objects.create(
        user=user, content=content, platform='linkedin', status='published', published_at=published_at,
    )
    Analytics.objects.create(post=post, likes=1, views=100, shares=0, comments=0, engagement_rate=engagement_rate)
    return post


class ComputeFormatRecommendationsTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='recouser', password='pass')

    def test_fewer_than_5_published_posts_returns_message(self):
        for i in range(3):
            _make_published_post(self.user, f'Post court {i}', days_ago=i, hour=9, engagement_rate=10.0)

        result = compute_format_recommendations(self.user)

        self.assertEqual(result['recommendations'], [])
        self.assertIn('Publiez plus', result['message'])

    def test_hashtags_dimension_picks_higher_engagement_bucket(self):
        for i in range(6):
            _make_published_post(self.user, f'Sans hashtag {i}', days_ago=i, hour=9, engagement_rate=5.0)
        for i in range(6):
            _make_published_post(self.user, f'Avec hashtag {i} #klark', days_ago=i + 10, hour=9, engagement_rate=50.0)

        result = compute_format_recommendations(self.user)

        top = result['recommendations'][0]
        self.assertEqual(top['dimension'], 'hashtags')
        self.assertEqual(top['valeur_optimale'], 'avec')
        self.assertEqual(top['engagement_moyen'], 50.0)

    def test_returns_at_most_3_recommendations(self):
        for i in range(6):
            _make_published_post(self.user, f'Post {i} avec ? et #tag', days_ago=i, hour=9, engagement_rate=20.0)

        result = compute_format_recommendations(self.user)

        self.assertLessEqual(len(result['recommendations']), 3)

    def test_confidence_levels(self):
        for i in range(3):
            _make_published_post(self.user, f'Faible confiance {i}', days_ago=i, hour=7, engagement_rate=10.0)
        for i in range(6):
            _make_published_post(self.user, f'Post moyen {i}', days_ago=i + 20, hour=12, engagement_rate=1.0)

        result = compute_format_recommendations(self.user)

        confidences = {r['dimension']: r['confiance'] for r in result['recommendations']}
        # "matin" (7h) n'a que 3 posts -> confiance faible
        matin_reco = next((r for r in result['recommendations'] if r.get('valeur_optimale') == 'matin'), None)
        if matin_reco:
            self.assertEqual(matin_reco['confiance'], 'faible')

    def test_posts_older_than_90_days_excluded(self):
        _make_published_post(self.user, 'Trop vieux', days_ago=100, hour=9, engagement_rate=99.0)
        for i in range(5):
            _make_published_post(self.user, f'Récent {i}', days_ago=i, hour=9, engagement_rate=1.0)

        result = compute_format_recommendations(self.user)

        rates = [r['engagement_moyen'] for r in result['recommendations']]
        self.assertNotIn(99.0, rates)

    def test_posts_without_analytics_are_ignored(self):
        Post.objects.create(
            user=self.user, content='Pas encore collecté', platform='linkedin',
            status='published', published_at=timezone.now(),
        )
        for i in range(5):
            _make_published_post(self.user, f'Avec analytics {i}', days_ago=i, hour=9, engagement_rate=10.0)

        result = compute_format_recommendations(self.user)

        self.assertIsInstance(result['recommendations'], list)


class RecommendationsViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='recoview', password='pass')
        self.client.force_authenticate(user=self.user)

    def test_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/analytics/recommendations/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_message_when_not_enough_posts(self):
        response = self.client.get('/analytics/recommendations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['recommendations'], [])
