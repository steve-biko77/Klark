from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch
from apps.articles.models import Article
from .models import Source
from .services import scrape_source


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


class ScrapeSourceServiceTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='scrapeuser', password='pass')

    def test_prefers_full_content_over_summary(self):
        feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel>
  <item>
    <title>Article Title</title>
    <link>https://example.com/article-1</link>
    <description>Short summary only.</description>
    <content:encoded><![CDATA[<p>Full rich article content.</p>]]></content:encoded>
  </item>
</channel>
</rss>"""
        source = Source.objects.create(user=self.user, url=feed_xml)
        scrape_source(source)

        article = Article.objects.get(source=source)
        self.assertIn('Full rich article content', article.content)

    def test_falls_back_to_summary_when_no_full_content(self):
        feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <item>
    <title>Article Title</title>
    <link>https://example.com/article-2</link>
    <description>Only a summary here.</description>
  </item>
</channel>
</rss>"""
        source = Source.objects.create(user=self.user, url=feed_xml)
        scrape_source(source)

        article = Article.objects.get(source=source)
        self.assertEqual(article.content, 'Only a summary here.')

    def test_bozo_feed_with_entries_still_imports_articles(self):
        feed_xml = """<rss version="2.0"><channel><item>
<title>A &amp B</title>
<link>https://example.com/article-3</link>
<description>Content despite bozo.</description>
</item></channel></rss>"""
        source = Source.objects.create(user=self.user, url=feed_xml)
        result = scrape_source(source)

        self.assertEqual(result['articles_added'], 1)
        source.refresh_from_db()
        self.assertEqual(source.status, 'active')

    def test_unparseable_feed_marks_source_error(self):
        source = Source.objects.create(user=self.user, url='not even xml at all just garbage text')
        result = scrape_source(source)

        self.assertEqual(result['articles_added'], 0)
        self.assertIn('error', result)
        source.refresh_from_db()
        self.assertEqual(source.status, 'error')


class ScrapeSourceScoringTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='scoreuser', password='pass')
        self.feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <item>
    <title>Article à scorer</title>
    <link>https://example.com/scored-article</link>
    <description>Un article sur la finance.</description>
  </item>
</channel>
</rss>"""

    @patch('apps.sources.services.score_article')
    def test_scores_article_when_profile_exists(self, mock_score):
        from apps.authentication.models import Profile
        Profile.objects.create(
            user=self.user, persona='TRADER',
            style_prompt='Direct', sector='Finance', tone='DIRECT',
        )
        mock_score.return_value = 82

        source = Source.objects.create(user=self.user, url=self.feed_xml)
        scrape_source(source)

        article = Article.objects.get(source=source)
        self.assertEqual(article.score, 82)
        mock_score.assert_called_once()
        self.assertEqual(mock_score.call_args.kwargs['persona'], 'TRADER')

    @patch('apps.sources.services.score_article')
    def test_score_defaults_to_zero_without_profile(self, mock_score):
        source = Source.objects.create(user=self.user, url=self.feed_xml)
        scrape_source(source)

        article = Article.objects.get(source=source)
        self.assertEqual(article.score, 0.0)
        mock_score.assert_not_called()

    @patch('apps.sources.services.score_article', side_effect=Exception('API down'))
    def test_scraping_succeeds_even_if_scoring_fails(self, mock_score):
        from apps.authentication.models import Profile
        Profile.objects.create(
            user=self.user, persona='TRADER',
            style_prompt='', sector='', tone='DIRECT',
        )

        source = Source.objects.create(user=self.user, url=self.feed_xml)
        result = scrape_source(source)

        self.assertEqual(result['articles_added'], 1)
        article = Article.objects.get(source=source)
        self.assertEqual(article.score, 0.0)
