from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status

from apps.sources.models import Source
from .models import Article, Alert, Notification
from .services import detect_alerts


class AlertEndpointTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='alertuser', password='pass')
        self.client.force_authenticate(user=self.user)

    def test_create_alert(self):
        response = self.client.post('/alerts/', {'keyword': 'Fed rate'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['keyword'], 'Fed rate')
        self.assertTrue(response.data['is_active'])

    def test_list_alerts_only_user_owned(self):
        Alert.objects.create(user=self.user, keyword='BTC')
        other = User.objects.create_user(username='other', password='pass')
        Alert.objects.create(user=other, keyword='ETH')

        response = self.client.get('/alerts/')
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['keyword'], 'BTC')

    def test_max_ten_active_alerts(self):
        for i in range(10):
            Alert.objects.create(user=self.user, keyword=f'mot{i}')

        response = self.client.post('/alerts/', {'keyword': 'mot11'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_alerts_dont_count_towards_max(self):
        for i in range(10):
            Alert.objects.create(user=self.user, keyword=f'mot{i}', is_active=False)

        response = self.client.post('/alerts/', {'keyword': 'mot11'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_deactivate_alert(self):
        alert = Alert.objects.create(user=self.user, keyword='BTC')
        response = self.client.patch(f'/alerts/{alert.id}/', {'is_active': False}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        alert.refresh_from_db()
        self.assertFalse(alert.is_active)

    def test_delete_alert(self):
        alert = Alert.objects.create(user=self.user, keyword='BTC')
        response = self.client.delete(f'/alerts/{alert.id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Alert.objects.filter(id=alert.id).exists())

    def test_cannot_modify_other_user_alert(self):
        other = User.objects.create_user(username='other2', password='pass')
        alert = Alert.objects.create(user=other, keyword='BTC')

        response = self.client.delete(f'/alerts/{alert.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class NotificationEndpointTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='notifuser', password='pass')
        self.client.force_authenticate(user=self.user)
        self.source = Source.objects.create(user=self.user, url='https://example.com/rss')
        self.article = Article.objects.create(
            source=self.source, title='La Fed relève ses taux', content='...', url='https://a.com'
        )

    def test_list_notifications(self):
        Notification.objects.create(user=self.user, article=self.article, keyword='Fed rate')

        response = self.client.get('/notifications/')
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['keyword'], 'Fed rate')
        self.assertEqual(response.data[0]['article_title'], 'La Fed relève ses taux')

    def test_mark_notification_read(self):
        notif = Notification.objects.create(user=self.user, article=self.article, keyword='Fed rate')

        response = self.client.patch(f'/notifications/{notif.id}/read/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_unread_count_in_list(self):
        Notification.objects.create(user=self.user, article=self.article, keyword='Fed rate', is_read=False)
        Notification.objects.create(user=self.user, article=self.article, keyword='BTC', is_read=True)

        response = self.client.get('/notifications/')
        unread = [n for n in response.data if not n['is_read']]
        self.assertEqual(len(unread), 1)


class DetectAlertsServiceTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='detectuser', password='pass')
        self.source = Source.objects.create(user=self.user, url='https://example.com/rss')

    def test_creates_notification_on_case_insensitive_match_in_title(self):
        Alert.objects.create(user=self.user, keyword='fed rate')
        article = Article.objects.create(
            source=self.source, title='THE FED RATE just changed', content='', url='https://a.com'
        )

        detect_alerts(article, self.user)

        self.assertEqual(Notification.objects.filter(user=self.user, article=article).count(), 1)

    def test_creates_notification_on_match_in_content(self):
        Alert.objects.create(user=self.user, keyword='BTC crash')
        article = Article.objects.create(
            source=self.source, title='Marchés', content='Un BTC crash a eu lieu hier.', url='https://a.com'
        )

        detect_alerts(article, self.user)

        self.assertEqual(Notification.objects.filter(user=self.user, article=article).count(), 1)

    def test_no_notification_for_inactive_alert(self):
        Alert.objects.create(user=self.user, keyword='BTC', is_active=False)
        article = Article.objects.create(
            source=self.source, title='BTC en hausse', content='', url='https://a.com'
        )

        detect_alerts(article, self.user)

        self.assertEqual(Notification.objects.filter(user=self.user, article=article).count(), 0)

    def test_no_match_no_notification(self):
        Alert.objects.create(user=self.user, keyword='inflation')
        article = Article.objects.create(
            source=self.source, title='Rien à voir', content='Contenu neutre.', url='https://a.com'
        )

        detect_alerts(article, self.user)

        self.assertEqual(Notification.objects.count(), 0)
