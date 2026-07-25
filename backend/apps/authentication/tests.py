from unittest.mock import patch
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from .models import OTPCode


class RegisterViewTest(APITestCase):

    def test_register_creates_user(self):
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'StrongPass123!',
        }
        response = self.client.post('/auth/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertTrue(User.objects.filter(username='testuser').exists())

    def test_register_duplicate_username(self):
        User.objects.create_user(username='testuser', password='pass')
        data = {'username': 'testuser', 'email': 'a@b.com', 'password': 'StrongPass123!'}
        response = self.client.post('/auth/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self):
        User.objects.create_user(username='other', email='dup@example.com', password='pass')
        data = {'username': 'newuser', 'email': 'dup@example.com', 'password': 'StrongPass123!'}
        response = self.client.post('/auth/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username='newuser').exists())


class LoginOTPViewTest(APITestCase):

    @patch('apps.authentication.views.send_mail')
    def test_login_sends_otp(self, mock_mail):
        User.objects.create_user(username='testuser', email='test@example.com', password='StrongPass123!')
        data = {'username': 'testuser', 'password': 'StrongPass123!'}
        response = self.client.post('/auth/login/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'otp_sent')
        self.assertIn('user_id', response.data)
        self.assertIn('email', response.data)
        self.assertTrue(mock_mail.called)

    def test_login_without_email_returns_400(self):
        User.objects.create_user(username='testuser', password='StrongPass123!')
        data = {'username': 'testuser', 'password': 'StrongPass123!'}
        response = self.client.post('/auth/login/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_wrong_password(self):
        User.objects.create_user(username='testuser', email='test@example.com', password='correct')
        data = {'username': 'testuser', 'password': 'wrong'}
        response = self.client.post('/auth/login/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class VerifyOTPViewTest(APITestCase):

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='pass')

    def test_verify_valid_otp_returns_tokens(self):
        otp = OTPCode.objects.create(
            user=self.user, code='123456',
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        response = self.client.post('/auth/verify-otp/', {
            'user_id': self.user.id, 'code': '123456',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_verify_wrong_code(self):
        OTPCode.objects.create(
            user=self.user, code='123456',
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        response = self.client.post('/auth/verify-otp/', {
            'user_id': self.user.id, 'code': '000000',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_expired_otp(self):
        OTPCode.objects.create(
            user=self.user, code='123456',
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        response = self.client.post('/auth/verify-otp/', {
            'user_id': self.user.id, 'code': '123456',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('expiré', response.data['error'])

    def test_verify_already_used_otp(self):
        OTPCode.objects.create(
            user=self.user, code='123456',
            expires_at=timezone.now() + timedelta(minutes=10),
            used=True,
        )
        response = self.client.post('/auth/verify-otp/', {
            'user_id': self.user.id, 'code': '123456',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class VerifyOTPLockoutTest(APITestCase):

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='lockuser', email='lock@example.com', password='pass')
        OTPCode.objects.create(
            user=self.user, code='123456',
            expires_at=timezone.now() + timedelta(minutes=10),
        )

    def test_locked_out_after_three_failed_attempts(self):
        for _ in range(3):
            response = self.client.post('/auth/verify-otp/', {
                'user_id': self.user.id, 'code': '000000',
            }, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post('/auth/verify-otp/', {
            'user_id': self.user.id, 'code': '123456',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_successful_verify_before_lockout_still_works(self):
        for _ in range(2):
            self.client.post('/auth/verify-otp/', {
                'user_id': self.user.id, 'code': '000000',
            }, format='json')

        response = self.client.post('/auth/verify-otp/', {
            'user_id': self.user.id, 'code': '123456',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PasswordResetViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', email='test@example.com', password='pass'
        )

    @patch('apps.authentication.views.send_mail')
    def test_password_reset_request_existing_email(self, mock_mail):
        response = self.client.post('/auth/password-reset/', {'email': 'test@example.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertTrue(mock_mail.called)

    @patch('apps.authentication.views.send_mail')
    def test_password_reset_request_unknown_email(self, mock_mail):
        response = self.client.post('/auth/password-reset/', {'email': 'unknown@example.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(mock_mail.called)
