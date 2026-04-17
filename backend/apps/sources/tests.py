from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch
from .models import Source


class SourcesViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.client.force_authenticate(user=self.user)

    def test_list_sources_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/sources/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_sources_empty(self):
        response = self.client.get('/sources/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_create_source(self):
        data = {'url': 'https://example.com/rss', 'name': 'Test Feed'}
        response = self.client.post('/sources/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['url'], 'https://example.com/rss')
        self.assertEqual(Source.objects.filter(user=self.user).count(), 1)

    def test_list_sources_only_user_owned(self):
        other_user = User.objects.create_user(username='other', password='pass')
        Source.objects.create(user=other_user, url='https://other.com/rss')
        Source.objects.create(user=self.user, url='https://mine.com/rss')

        response = self.client.get('/sources/')
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['url'], 'https://mine.com/rss')

    @patch('apps.sources.views.scrape_source')
    def test_scrape_source(self, mock_scrape):
        mock_scrape.return_value = {'articles_added': 3, 'total_found': 5}
        source = Source.objects.create(user=self.user, url='https://example.com/rss')

        response = self.client.post(f'/sources/{source.id}/scrape/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['articles_added'], 3)

    def test_scrape_source_not_found(self):
        response = self.client.post('/sources/9999/scrape/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
