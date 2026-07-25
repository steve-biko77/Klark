from unittest.mock import patch
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from .models import OTPCode, Profile


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


class ProfileModelTest(APITestCase):

    def test_create_profile_with_persona_and_tone(self):
        user = User.objects.create_user(username='produser', password='pass')
        profile = Profile.objects.create(
            user=user,
            persona='TRADER',
            style_prompt='Direct et factuel, orienté marchés financiers.',
            sector='Finance',
            tone='EXPERT',
        )
        self.assertEqual(profile.user, user)
        self.assertEqual(profile.get_persona_display(), 'Trader')
        self.assertEqual(profile.get_tone_display(), 'Expert')

    def test_profile_is_one_to_one_with_user(self):
        user = User.objects.create_user(username='onlyone', password='pass')
        Profile.objects.create(user=user, persona='CREATEUR', style_prompt='x', sector='Média', tone='DIRECT')
        with self.assertRaises(Exception):
            Profile.objects.create(user=user, persona='PASSIONNE', style_prompt='y', sector='Tech', tone='ACCESSIBLE')


class ProfileEndpointTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='profileuser', password='pass')
        self.client.force_authenticate(user=self.user)

    def test_get_profile_creates_with_defaults_if_missing(self):
        response = self.client.get('/profile/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['persona'], 'CREATEUR')
        self.assertEqual(response.data['tone'], 'EXPERT')
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

    def test_get_profile_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_profile_updates_fields(self):
        response = self.client.patch('/profile/', {
            'persona': 'TRADER',
            'sector': 'Finance et marchés',
            'tone': 'DIRECT',
            'style_prompt': 'Posts courts et percutants, je commence par une question provoc.',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['persona'], 'TRADER')
        self.assertEqual(response.data['sector'], 'Finance et marchés')
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.persona, 'TRADER')
        self.assertEqual(profile.tone, 'DIRECT')

    def test_patch_profile_creates_if_missing(self):
        self.assertFalse(Profile.objects.filter(user=self.user).exists())
        response = self.client.patch('/profile/', {'sector': 'Tech'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

    def test_patch_profile_rejects_invalid_persona(self):
        response = self.client.patch('/profile/', {'persona': 'NOT_A_PERSONA'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_profile_allows_blank_sector_and_style_prompt(self):
        response = self.client.patch('/profile/', {
            'persona': 'TRADER',
            'tone': 'DIRECT',
            'sector': '',
            'style_prompt': '',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['sector'], '')
