from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Source
from .services import detect_feed_urls


def _feed_result(entries):
    result = MagicMock()
    result.entries = entries
    return result


class DetectFeedUrlsTest(TestCase):

    @patch('apps.sources.services.feedparser.parse')
    def test_url_already_a_valid_feed_returns_itself(self, mock_parse):
        mock_parse.return_value = _feed_result([{'title': 'A'}])

        result = detect_feed_urls('https://example.com/rss')

        self.assertEqual(result, ['https://example.com/rss'])

    @patch('apps.sources.services._fetch_html')
    @patch('apps.sources.services.feedparser.parse')
    def test_finds_feed_link_tag_in_html(self, mock_parse, mock_fetch_html):
        mock_parse.return_value = _feed_result([])
        mock_fetch_html.return_value = '''
            <html><head>
            <link rel="alternate" type="application/rss+xml" href="/feed.rss">
            </head></html>
        '''

        result = detect_feed_urls('https://techcrunch.com')

        self.assertEqual(result, ['https://techcrunch.com/feed.rss'])

    @patch('apps.sources.services._fetch_html')
    @patch('apps.sources.services.feedparser.parse')
    def test_finds_multiple_feed_link_tags(self, mock_parse, mock_fetch_html):
        mock_parse.return_value = _feed_result([])
        mock_fetch_html.return_value = '''
            <html><head>
            <link rel="alternate" type="application/rss+xml" href="/feed">
            <link rel="alternate" type="application/atom+xml" href="/feed/comments">
            </head></html>
        '''

        result = detect_feed_urls('https://example.com')

        self.assertEqual(len(result), 2)

    @patch('apps.sources.services._fetch_html')
    @patch('apps.sources.services.feedparser.parse')
    def test_falls_back_to_conventional_paths(self, mock_parse, mock_fetch_html):
        mock_fetch_html.return_value = '<html><head></head></html>'

        def parse_side_effect(url):
            if url == 'https://example.com/feed':
                return _feed_result([{'title': 'A'}])
            return _feed_result([])

        mock_parse.side_effect = parse_side_effect

        result = detect_feed_urls('https://example.com')

        self.assertEqual(result, ['https://example.com/feed'])

    @patch('apps.sources.services._fetch_html')
    @patch('apps.sources.services.feedparser.parse')
    def test_returns_empty_when_nothing_found(self, mock_parse, mock_fetch_html):
        mock_parse.return_value = _feed_result([])
        mock_fetch_html.return_value = '<html><head></head></html>'

        result = detect_feed_urls('https://example.com')

        self.assertEqual(result, [])

    @patch('apps.sources.services._fetch_html')
    @patch('apps.sources.services.feedparser.parse')
    def test_unreachable_url_returns_empty(self, mock_parse, mock_fetch_html):
        mock_parse.return_value = _feed_result([])
        mock_fetch_html.return_value = None

        result = detect_feed_urls('https://this-does-not-exist.invalid')

        self.assertEqual(result, [])


class SourceCreateWithDetectionTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='detectuser', password='pass')
        self.client.force_authenticate(user=self.user)

    @patch('apps.sources.views.detect_feed_urls')
    def test_create_source_direct_feed_url(self, mock_detect):
        mock_detect.return_value = ['https://example.com/rss']

        response = self.client.post('/sources/', {'url': 'https://example.com/rss', 'name': 'Test Feed'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['url'], 'https://example.com/rss')
        self.assertEqual(Source.objects.filter(user=self.user).count(), 1)

    @patch('apps.sources.views.detect_feed_urls')
    def test_create_source_auto_detects_from_homepage(self, mock_detect):
        mock_detect.return_value = ['https://techcrunch.com/feed/']

        response = self.client.post('/sources/', {'url': 'https://techcrunch.com', 'name': 'TC'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['url'], 'https://techcrunch.com/feed/')

    @patch('apps.sources.views.detect_feed_urls')
    def test_no_feed_detected_returns_400(self, mock_detect):
        mock_detect.return_value = []

        response = self.client.post('/sources/', {'url': 'https://no-feed-here.com'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('url', response.data)

    @patch('apps.sources.views.detect_feed_urls')
    def test_multiple_candidates_returns_choices_without_creating(self, mock_detect):
        mock_detect.return_value = ['https://example.com/feed', 'https://example.com/comments-feed']

        response = self.client.post('/sources/', {'url': 'https://example.com'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['candidates']), 2)
        self.assertEqual(Source.objects.filter(user=self.user).count(), 0)


class SourceDetectViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='detectview', password='pass')
        self.client.force_authenticate(user=self.user)

    def test_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.post('/sources/detect/', {'url': 'https://example.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('apps.sources.views.detect_feed_urls')
    def test_returns_candidates_without_creating_source(self, mock_detect):
        mock_detect.return_value = ['https://example.com/feed']

        response = self.client.post('/sources/detect/', {'url': 'https://example.com'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['candidates'], ['https://example.com/feed'])
        self.assertEqual(Source.objects.count(), 0)

    def test_missing_url_returns_400(self):
        response = self.client.post('/sources/detect/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SourcePatchTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='patchuser', password='pass')
        self.client.force_authenticate(user=self.user)
        self.source = Source.objects.create(user=self.user, url='https://a.com/rss', name='Old name')

    def test_patch_updates_name(self):
        response = self.client.patch(f'/sources/{self.source.id}/', {'name': 'New name'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.source.refresh_from_db()
        self.assertEqual(self.source.name, 'New name')

    def test_patch_other_user_source_forbidden(self):
        other = User.objects.create_user(username='other5', password='pass')
        source = Source.objects.create(user=other, url='https://b.com/rss')
        response = self.client.patch(f'/sources/{source.id}/', {'name': 'Hack'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SourceArticlesCountTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='countuser', password='pass')
        self.client.force_authenticate(user=self.user)

    def test_articles_count_reflects_related_articles(self):
        from apps.articles.models import Article
        source = Source.objects.create(user=self.user, url='https://a.com/rss')
        Article.objects.create(source=source, title='A1', url='https://a.com/1')
        Article.objects.create(source=source, title='A2', url='https://a.com/2')

        response = self.client.get('/sources/')

        self.assertEqual(response.data[0]['articles_count'], 2)
