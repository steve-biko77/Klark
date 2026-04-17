from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from supabase import create_client
from django.conf import settings


class SupabaseUser:
    """Objet utilisateur minimaliste injecté dans request.user."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.is_authenticated = True
        self.is_active = True

    def __str__(self):
        return str(self.user_id)


class SupabaseAuthentication(BaseAuthentication):
    """Valide le JWT Supabase via le SDK et injecte un SupabaseUser."""

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ', 1)[1]

        try:
            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
            response = client.auth.get_user(token)
            if not response or not response.user:
                raise AuthenticationFailed('Token invalide')
            return (SupabaseUser(response.user.id), token)
        except AuthenticationFailed:
            raise
        except Exception:
            raise AuthenticationFailed('Token invalide ou expiré')
