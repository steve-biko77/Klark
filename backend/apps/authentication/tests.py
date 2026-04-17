from unittest.mock import patch, MagicMock
from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import AuthenticationFailed
from django.test import TestCase
from .backends import SupabaseAuthentication, SupabaseUser
import uuid

class SupabaseAuthenticationTest(TestCase):

    def setUp(self):
        self.auth = SupabaseAuthentication()
        self.factory = APIRequestFactory()

    def test_no_auth_header_returns_none(self):
        request = self.factory.get('/sources/')
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    @patch('apps.authentication.backends.create_client')
    def test_valid_token_returns_user(self, mock_create_client):
        user_id = str(uuid.uuid4())
        mock_supabase = MagicMock()
        mock_user_response = MagicMock()
        mock_user_response.user.id = user_id
        mock_supabase.auth.get_user.return_value = mock_user_response
        mock_create_client.return_value = mock_supabase

        request = self.factory.get('/sources/', HTTP_AUTHORIZATION='Bearer valid-token')
        user, token = self.auth.authenticate(request)

        self.assertIsInstance(user, SupabaseUser)
        self.assertEqual(str(user.user_id), user_id)
        self.assertTrue(user.is_authenticated)

    @patch('apps.authentication.backends.create_client')
    def test_invalid_token_raises_error(self, mock_create_client):
        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.side_effect = Exception("Token invalide")
        mock_create_client.return_value = mock_supabase

        request = self.factory.get('/sources/', HTTP_AUTHORIZATION='Bearer bad-token')
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(request)
