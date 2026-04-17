from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status


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

    def test_login_returns_tokens(self):
        User.objects.create_user(username='testuser', password='StrongPass123!')
        data = {'username': 'testuser', 'password': 'StrongPass123!'}
        response = self.client.post('/auth/login/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_wrong_password(self):
        User.objects.create_user(username='testuser', password='correct')
        data = {'username': 'testuser', 'password': 'wrong'}
        response = self.client.post('/auth/login/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
