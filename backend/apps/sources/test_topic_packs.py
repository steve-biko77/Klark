from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Source, TopicPack
from .services import activate_topic_pack


class ActivateTopicPackServiceTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='packuser', password='pass')
        self.pack = TopicPack.objects.create(
            name='Trader Finance', persona='TRADER',
            sources=[
                {'name': 'CoinDesk', 'url': 'https://www.coindesk.com'},
                {'name': 'MarketWatch', 'url': 'https://www.marketwatch.com'},
            ],
        )

    @patch('apps.sources.services.scrape_source')
    @patch('apps.sources.services.detect_feed_urls')
    def test_creates_a_source_per_pack_entry(self, mock_detect, mock_scrape):
        mock_detect.side_effect = [['https://www.coindesk.com/feed'], ['https://www.marketwatch.com/feed']]
        mock_scrape.return_value = {'articles_added': 0, 'total_found': 0}

        created = activate_topic_pack(self.pack, self.user)

        self.assertEqual(len(created), 2)
        self.assertEqual(Source.objects.filter(user=self.user).count(), 2)
        self.assertEqual(mock_scrape.call_count, 2)

    @patch('apps.sources.services.scrape_source')
    @patch('apps.sources.services.detect_feed_urls')
    def test_skips_entries_with_no_detectable_feed(self, mock_detect, mock_scrape):
        mock_detect.side_effect = [[], ['https://www.marketwatch.com/feed']]
        mock_scrape.return_value = {'articles_added': 0, 'total_found': 0}

        created = activate_topic_pack(self.pack, self.user)

        self.assertEqual(len(created), 1)
        self.assertEqual(Source.objects.filter(user=self.user).count(), 1)

    @patch('apps.sources.services.scrape_source')
    @patch('apps.sources.services.detect_feed_urls')
    def test_uses_first_candidate_when_multiple_found(self, mock_detect, mock_scrape):
        mock_detect.side_effect = [
            ['https://www.coindesk.com/feed', 'https://www.coindesk.com/comments-feed'],
            ['https://www.marketwatch.com/feed'],
        ]
        mock_scrape.return_value = {'articles_added': 0, 'total_found': 0}

        activate_topic_pack(self.pack, self.user)

        self.assertEqual(Source.objects.get(url__icontains='coindesk').url, 'https://www.coindesk.com/feed')


class TopicPackListViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='listpack', password='pass')
        self.client.force_authenticate(user=self.user)
        TopicPack.objects.create(name='Trader Finance', persona='TRADER', sources=[])
        TopicPack.objects.create(name='Créateur Tech', persona='CREATEUR', sources=[])
        TopicPack.objects.create(name='Inactif', persona='TRADER', sources=[], is_active=False)

    def test_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/topic-packs/?persona=TRADER')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_filters_by_persona(self):
        response = self.client.get('/topic-packs/?persona=TRADER')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p['name'] for p in response.data]
        self.assertIn('Trader Finance', names)
        self.assertNotIn('Créateur Tech', names)

    def test_excludes_inactive_packs(self):
        response = self.client.get('/topic-packs/?persona=TRADER')
        names = [p['name'] for p in response.data]
        self.assertNotIn('Inactif', names)

    def test_no_persona_filter_returns_all_active(self):
        response = self.client.get('/topic-packs/')
        names = [p['name'] for p in response.data]
        self.assertIn('Trader Finance', names)
        self.assertIn('Créateur Tech', names)
        self.assertNotIn('Inactif', names)


class TopicPackActivateViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='activateuser', password='pass')
        self.client.force_authenticate(user=self.user)
        self.pack = TopicPack.objects.create(
            name='Trader Finance', persona='TRADER',
            sources=[{'name': 'CoinDesk', 'url': 'https://www.coindesk.com'}],
        )

    def test_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(f'/topic-packs/{self.pack.id}/activate/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('apps.sources.views.activate_topic_pack')
    def test_activates_pack_and_returns_created_sources(self, mock_activate):
        mock_activate.return_value = [Source.objects.create(user=self.user, url='https://a.com/feed', name='A')]

        response = self.client.post(f'/topic-packs/{self.pack.id}/activate/')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['sources']), 1)

    def test_unknown_pack_returns_404(self):
        response = self.client.post('/topic-packs/9999/activate/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TopicPackAdminTest(TestCase):

    def test_registered_in_admin(self):
        from django.contrib import admin
        self.assertIn(TopicPack, admin.site._registry)
