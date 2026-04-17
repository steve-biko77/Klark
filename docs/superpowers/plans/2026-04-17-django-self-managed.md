# Django Backend Self-Managed — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finaliser le backend Django Klark sans Supabase — PostgreSQL + auth JWT gérés en interne, orchestrés par Docker Compose.

**Architecture:** Django 5.2 + DRF + djangorestframework-simplejwt pour l'auth. PostgreSQL dans Docker (déjà défini dans docker-compose.yml). Un app `authentication` expose register/login. Les apps métier (`sources`, `articles`, `posts`) utilisent `request.user` Django standard. Migrations normales (pas de fake-initial).

**Tech Stack:** Django 5.2, DRF 3.17, djangorestframework-simplejwt, PostgreSQL 15 (Docker), psycopg2-binary, dj-database-url, python-decouple, feedparser, anthropic SDK

---

## État actuel de la branche `refactor/django-backend`

Ce qui est déjà fait et **à conserver** :
- Structure `backend/apps/` + 4 apps scaffoldées via CLI ✓
- `apps/*/apps.py` avec noms dotted (`apps.sources`, etc.) ✓
- `backend/config/settings.py` partiellement configuré (à mettre à jour)
- `backend/apps/authentication/backends.py` (SupabaseAuthentication → à remplacer)
- `docker-compose.yml` à la racine (postgres + redis déjà là)

---

## Structure des fichiers

```
backend/
  manage.py
  requirements.txt                    ← créé
  Dockerfile                          ← créé
  .env.example                        ← mis à jour (sans Supabase)
  config/
    settings.py                       ← mis à jour
    urls.py                           ← mis à jour
  apps/
    authentication/
      backends.py                     ← supprimé (remplacé par simplejwt)
      serializers.py                  ← créé (RegisterSerializer)
      views.py                        ← créé (RegisterView)
      urls.py                         ← créé
      tests.py                        ← mis à jour
    sources/
      models.py, serializers.py, services.py, views.py, urls.py
    articles/
      models.py, serializers.py, views.py, urls.py
    posts/
      models.py, serializers.py, services.py, views.py, urls.py

docker-compose.yml                    ← mis à jour (healthcheck, volumes)
```

---

## Task 1 : requirements.txt + Dockerfile + docker-compose.yml

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/Dockerfile`
- Modify: `docker-compose.yml`
- Modify: `backend/.env.example`

- [ ] **Step 1 : Créer requirements.txt**

```text
# backend/requirements.txt
Django==5.2.13
djangorestframework==3.17.1
djangorestframework-simplejwt==5.5.0
django-cors-headers==4.9.0
dj-database-url==2.3.0
python-decouple==3.8
psycopg2-binary==2.9.11
feedparser==6.0.12
anthropic==0.94.1
```

- [ ] **Step 2 : Installer simplejwt dans le venv**

```bash
cd backend && .venv/bin/pip install djangorestframework-simplejwt==5.5.0
```

Expected : `Successfully installed djangorestframework-simplejwt-5.5.0`

- [ ] **Step 3 : Créer le Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

- [ ] **Step 4 : Mettre à jour docker-compose.yml**

```yaml
# docker-compose.yml (à la racine du projet)
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: klark
      POSTGRES_USER: klark
      POSTGRES_PASSWORD: klark_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U klark -d klark"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: ./backend/.env
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./backend:/app

  worker:
    build: ./workers
    env_file: ./backend/.env
    depends_on:
      - redis

volumes:
  postgres_data:
```

- [ ] **Step 5 : Mettre à jour backend/.env.example**

```env
# Django
SECRET_KEY=django-insecure-change-me-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://klark:klark_dev@localhost:5432/klark

# Anthropic
ANTHROPIC_API_KEY=your_anthropic_key
```

- [ ] **Step 6 : Commit**

```bash
git add backend/requirements.txt backend/Dockerfile backend/.env.example docker-compose.yml
git commit -m "feat: requirements.txt, Dockerfile, docker-compose.yml self-managed"
```

---

## Task 2 : Mise à jour settings.py (suppression Supabase, ajout simplejwt)

**Files:**
- Modify: `backend/config/settings.py`
- Delete: `backend/apps/authentication/backends.py`

- [ ] **Step 1 : Supprimer backends.py (Supabase)**

```bash
rm backend/apps/authentication/backends.py
```

- [ ] **Step 2 : Réécrire settings.py**

```python
# backend/config/settings.py
import sys
from pathlib import Path
from decouple import config
from datetime import timedelta
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = [h.strip() for h in config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')]

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'apps.authentication',
    'apps.sources',
    'apps.articles',
    'apps.posts',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

_TESTING = 'test' in sys.argv

if _TESTING:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
else:
    DATABASES = {
        'default': dj_database_url.config(default=config('DATABASE_URL'))
    }

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
]
CORS_ALLOW_CREDENTIALS = True

# Anthropic
ANTHROPIC_API_KEY = config('ANTHROPIC_API_KEY')
```

- [ ] **Step 3 : Vérifier**

```bash
cd backend && .venv/bin/python manage.py check
```

Expected : `System check identified no issues (0 silenced).`

- [ ] **Step 4 : Commit**

```bash
git add backend/config/settings.py backend/apps/authentication/backends.py
git commit -m "feat: settings.py self-managed — simplejwt, suppression Supabase"
```

---

## Task 3 : App authentication — register + login endpoints

**Files:**
- Create: `backend/apps/authentication/serializers.py`
- Modify: `backend/apps/authentication/views.py`
- Create: `backend/apps/authentication/urls.py`
- Modify: `backend/apps/authentication/tests.py`

- [ ] **Step 1 : Écrire les tests**

```python
# backend/apps/authentication/tests.py
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
```

- [ ] **Step 2 : Lancer les tests pour vérifier l'échec**

```bash
cd backend && .venv/bin/python manage.py test apps.authentication -v 2
```

Expected : 404 ou ImportError — URLs pas encore définies

- [ ] **Step 3 : Créer le serializer**

```python
# backend/apps/authentication/serializers.py
from django.contrib.auth.models import User
from rest_framework import serializers


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
        )
```

- [ ] **Step 4 : Créer la view register**

```python
# backend/apps/authentication/views.py
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

- [ ] **Step 5 : Créer les URLs**

```python
# backend/apps/authentication/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import RegisterView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', TokenObtainPairView.as_view(), name='auth-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
]
```

- [ ] **Step 6 : Câbler dans config/urls.py (temporaire pour ce test)**

```python
# backend/config/urls.py
from django.urls import path, include
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    return Response({'status': 'ok', 'service': 'klark-api'})


urlpatterns = [
    path('health/', health, name='health'),
    path('auth/', include('apps.authentication.urls')),
    path('sources/', include('apps.sources.urls')),
    path('articles/', include('apps.articles.urls')),
    path('posts/', include('apps.posts.urls')),
]
```

Note: les URLs sources/articles/posts n'existent pas encore — Django les ignorera tant qu'elles ne sont pas créées. Si `manage.py check` échoue à cause de ça, commenter temporairement ces lignes.

- [ ] **Step 7 : Lancer les tests**

```bash
cd backend && .venv/bin/python manage.py test apps.authentication -v 2
```

Expected : `OK (4 tests)`

- [ ] **Step 8 : Commit**

```bash
git add backend/apps/authentication/ backend/config/urls.py
git commit -m "feat: auth register/login avec simplejwt"
```

---

## Task 4 : Modèles Django (sources, articles, posts)

**Files:**
- Modify: `backend/apps/sources/models.py`
- Modify: `backend/apps/articles/models.py`
- Modify: `backend/apps/posts/models.py`

- [ ] **Step 1 : Modèle Source**

```python
# backend/apps/sources/models.py
from django.db import models
from django.contrib.auth.models import User


class Source(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sources')
    url = models.TextField()
    name = models.TextField(blank=True, default='')
    type = models.TextField(default='rss')
    status = models.TextField(default='pending')
    last_crawled = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name or self.url} ({self.user})"
```

- [ ] **Step 2 : Modèle Article**

```python
# backend/apps/articles/models.py
from django.db import models
from apps.sources.models import Source


class Article(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='articles')
    title = models.TextField()
    content = models.TextField(blank=True, default='')
    url = models.TextField(blank=True, default='')
    score = models.FloatField(default=0.0)
    published_at = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
```

- [ ] **Step 3 : Modèle Post**

```python
# backend/apps/posts/models.py
from django.db import models
from django.contrib.auth.models import User
from apps.articles.models import Article

PLATFORM_CHOICES = [
    ('linkedin', 'LinkedIn'),
    ('twitter', 'Twitter'),
    ('blog', 'Blog'),
]

STATUS_CHOICES = [
    ('draft', 'Brouillon'),
    ('published', 'Publié'),
]


class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    article = models.ForeignKey(Article, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    content = models.TextField()
    platform = models.TextField(choices=PLATFORM_CHOICES, default='linkedin')
    status = models.TextField(choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.platform} — {self.content[:50]}"
```

- [ ] **Step 4 : Vérifier**

```bash
cd backend && .venv/bin/python manage.py check
```

Expected : `System check identified no issues (0 silenced).`

- [ ] **Step 5 : Commit**

```bash
git add backend/apps/sources/models.py backend/apps/articles/models.py backend/apps/posts/models.py
git commit -m "feat: modèles Source, Article, Post avec FK Django"
```

---

## Task 5 : Migrations

**Files:**
- Create: `backend/apps/sources/migrations/0001_initial.py` (généré)
- Create: `backend/apps/articles/migrations/0001_initial.py` (généré)
- Create: `backend/apps/posts/migrations/0001_initial.py` (généré)

> **Note :** Les migrations sont générées et commitées maintenant. Elles seront appliquées (`migrate`) au démarrage Docker ou manuellement avec la DB Postgres locale.

- [ ] **Step 1 : Générer les migrations**

```bash
cd backend && .venv/bin/python manage.py makemigrations
```

Expected :
```
Migrations for 'sources':
  apps/sources/migrations/0001_initial.py
Migrations for 'articles':
  apps/articles/migrations/0001_initial.py
Migrations for 'posts':
  apps/posts/migrations/0001_initial.py
```

- [ ] **Step 2 : Commit**

```bash
git add backend/apps/sources/migrations/ backend/apps/articles/migrations/ backend/apps/posts/migrations/
git commit -m "feat: migrations initiales sources, articles, posts"
```

---

## Task 6 : App sources — serializer, service, views, urls

**Files:**
- Create: `backend/apps/sources/serializers.py`
- Create: `backend/apps/sources/services.py`
- Modify: `backend/apps/sources/views.py`
- Create: `backend/apps/sources/urls.py`

- [ ] **Step 1 : Écrire les tests**

```python
# backend/apps/sources/tests.py
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
```

- [ ] **Step 2 : Lancer les tests pour vérifier l'échec**

```bash
cd backend && .venv/bin/python manage.py test apps.sources -v 2
```

Expected : erreur — serializers/views/urls manquants

- [ ] **Step 3 : Créer le serializer**

```python
# backend/apps/sources/serializers.py
from rest_framework import serializers
from .models import Source


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = ['id', 'url', 'name', 'type', 'status', 'last_crawled', 'created_at']
        read_only_fields = ['id', 'type', 'status', 'last_crawled', 'created_at']
```

- [ ] **Step 4 : Créer le service scraper**

```python
# backend/apps/sources/services.py
import feedparser
from datetime import datetime, timezone
from apps.articles.models import Article
from .models import Source


def scrape_source(source: Source) -> dict:
    feed = feedparser.parse(source.url)

    if feed.bozo:
        source.status = 'error'
        source.save(update_fields=['status'])
        return {'error': 'Flux RSS invalide', 'articles_added': 0}

    articles_added = 0
    for entry in feed.entries[:10]:
        link = entry.get('link', '')
        if Article.objects.filter(source=source, url=link).exists():
            continue
        Article.objects.create(
            source=source,
            title=entry.get('title', 'Sans titre'),
            content=entry.get('summary', entry.get('description', '')),
            url=link,
            score=0.0,
            published_at=entry.get('published', None),
        )
        articles_added += 1

    source.status = 'active'
    source.last_crawled = datetime.now(timezone.utc)
    source.save(update_fields=['status', 'last_crawled'])

    return {
        'source_id': source.id,
        'articles_added': articles_added,
        'total_found': len(feed.entries),
    }
```

- [ ] **Step 5 : Créer les views**

```python
# backend/apps/sources/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Source
from .serializers import SourceSerializer
from .services import scrape_source


class SourceListCreateView(APIView):

    def get(self, request):
        sources = Source.objects.filter(user=request.user)
        return Response(SourceSerializer(sources, many=True).data)

    def post(self, request):
        serializer = SourceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, type='rss', status='pending')
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SourceScrapeView(APIView):

    def post(self, request, source_id):
        source = get_object_or_404(Source, id=source_id, user=request.user)
        result = scrape_source(source)
        return Response(result)
```

- [ ] **Step 6 : Créer les URLs**

```python
# backend/apps/sources/urls.py
from django.urls import path
from .views import SourceListCreateView, SourceScrapeView

urlpatterns = [
    path('', SourceListCreateView.as_view(), name='sources-list'),
    path('<int:source_id>/scrape/', SourceScrapeView.as_view(), name='source-scrape'),
]
```

- [ ] **Step 7 : Lancer les tests**

```bash
cd backend && .venv/bin/python manage.py test apps.sources -v 2
```

Expected : `OK (6 tests)`

- [ ] **Step 8 : Commit**

```bash
git add backend/apps/sources/
git commit -m "feat: app sources — serializer, scraper service, views, urls"
```

---

## Task 7 : App articles — serializer, views, urls

**Files:**
- Create: `backend/apps/articles/serializers.py`
- Modify: `backend/apps/articles/views.py`
- Create: `backend/apps/articles/urls.py`

- [ ] **Step 1 : Écrire les tests**

```python
# backend/apps/articles/tests.py
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from apps.sources.models import Source
from apps.articles.models import Article


class ArticlesViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.client.force_authenticate(user=self.user)
        self.source = Source.objects.create(user=self.user, url='https://example.com/rss')

    def test_list_articles_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/articles/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_articles_returns_only_user_articles(self):
        Article.objects.create(source=self.source, title='Mon article', url='https://a.com')

        other_user = User.objects.create_user(username='other', password='pass')
        other_source = Source.objects.create(user=other_user, url='https://other.com/rss')
        Article.objects.create(source=other_source, title='Autre article', url='https://b.com')

        response = self.client.get('/articles/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Mon article')

    def test_list_articles_empty_if_no_sources(self):
        user2 = User.objects.create_user(username='user2', password='pass')
        self.client.force_authenticate(user=user2)
        response = self.client.get('/articles/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])
```

- [ ] **Step 2 : Lancer pour vérifier l'échec**

```bash
cd backend && .venv/bin/python manage.py test apps.articles -v 2
```

Expected : erreur — serializers/views/urls manquants

- [ ] **Step 3 : Créer le serializer**

```python
# backend/apps/articles/serializers.py
from rest_framework import serializers
from .models import Article


class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ['id', 'source_id', 'title', 'content', 'url', 'score', 'published_at', 'created_at']
        read_only_fields = fields
```

- [ ] **Step 4 : Créer la view**

```python
# backend/apps/articles/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Article
from .serializers import ArticleSerializer


class ArticleListView(APIView):

    def get(self, request):
        articles = Article.objects.filter(source__user=request.user)
        return Response(ArticleSerializer(articles, many=True).data)
```

- [ ] **Step 5 : Créer les URLs**

```python
# backend/apps/articles/urls.py
from django.urls import path
from .views import ArticleListView

urlpatterns = [
    path('', ArticleListView.as_view(), name='articles-list'),
]
```

- [ ] **Step 6 : Lancer les tests**

```bash
cd backend && .venv/bin/python manage.py test apps.articles -v 2
```

Expected : `OK (3 tests)`

- [ ] **Step 7 : Commit**

```bash
git add backend/apps/articles/
git commit -m "feat: app articles — serializer, view, urls"
```

---

## Task 8 : App posts — serializer, service IA, views, urls

**Files:**
- Create: `backend/apps/posts/serializers.py`
- Create: `backend/apps/posts/services.py`
- Modify: `backend/apps/posts/views.py`
- Create: `backend/apps/posts/urls.py`

- [ ] **Step 1 : Écrire les tests**

```python
# backend/apps/posts/tests.py
from unittest.mock import patch
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from apps.sources.models import Source
from apps.articles.models import Article
from apps.posts.models import Post


class PostsViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.client.force_authenticate(user=self.user)
        self.source = Source.objects.create(user=self.user, url='https://example.com/rss')
        self.article = Article.objects.create(
            source=self.source, title='Titre test', content='Contenu test', url='https://a.com'
        )

    def test_list_posts_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/posts/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_posts_only_user_owned(self):
        Post.objects.create(user=self.user, content='Mon post', platform='linkedin')
        other = User.objects.create_user(username='other', password='pass')
        Post.objects.create(user=other, content='Autre post', platform='twitter')

        response = self.client.get('/posts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    @patch('apps.posts.views.generate_post')
    def test_generate_post(self, mock_generate):
        mock_generate.return_value = 'Contenu généré par IA'
        data = {'article_id': self.article.id, 'platform': 'linkedin'}
        response = self.client.post('/posts/generate/', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], 'Contenu généré par IA')
        self.assertEqual(response.data['platform'], 'linkedin')
        self.assertEqual(Post.objects.filter(user=self.user).count(), 1)

    def test_generate_post_article_not_found(self):
        data = {'article_id': 9999, 'platform': 'linkedin'}
        response = self.client.post('/posts/generate/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
```

- [ ] **Step 2 : Lancer pour vérifier l'échec**

```bash
cd backend && .venv/bin/python manage.py test apps.posts -v 2
```

Expected : erreur — serializers/views/urls manquants

- [ ] **Step 3 : Créer le serializer**

```python
# backend/apps/posts/serializers.py
from rest_framework import serializers
from .models import Post


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['id', 'article_id', 'content', 'platform', 'status', 'created_at']
        read_only_fields = ['id', 'status', 'created_at']
```

- [ ] **Step 4 : Créer le service IA**

```python
# backend/apps/posts/services.py
import anthropic
from django.conf import settings

_PLATFORM_INSTRUCTIONS = {
    'linkedin': 'un post LinkedIn professionnel, engageant, avec des sauts de ligne, maximum 1300 caractères',
    'twitter': 'un tweet percutant, maximum 280 caractères, sans hashtags excessifs',
    'blog': 'une introduction de blog structurée, 3 paragraphes, ton informatif',
}


def generate_post(article_title: str, article_content: str, platform: str = 'linkedin', style_prompt: str = '') -> str:
    instruction = _PLATFORM_INSTRUCTIONS.get(platform, _PLATFORM_INSTRUCTIONS['linkedin'])
    style = f"\nStyle de l'auteur : {style_prompt}" if style_prompt else ''

    prompt = f"""Tu es un expert en création de contenu digital.
A partir de cet article, rédige {instruction}.{style}

Titre de l'article : {article_title}

Contenu : {article_content[:2000]}

Rédige uniquement le post, sans explication ni commentaire."""

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=1024,
        messages=[{'role': 'user', 'content': prompt}],
    )
    return message.content[0].text
```

- [ ] **Step 5 : Créer les views**

```python
# backend/apps/posts/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from apps.articles.models import Article
from .models import Post
from .serializers import PostSerializer
from .services import generate_post


class PostListView(APIView):

    def get(self, request):
        posts = Post.objects.filter(user=request.user)
        return Response(PostSerializer(posts, many=True).data)


class PostGenerateView(APIView):

    def post(self, request):
        article_id = request.data.get('article_id')
        platform = request.data.get('platform', 'linkedin')

        article = get_object_or_404(Article, id=article_id, source__user=request.user)

        content = generate_post(
            article_title=article.title,
            article_content=article.content,
            platform=platform,
        )

        post = Post.objects.create(
            user=request.user,
            article=article,
            content=content,
            platform=platform,
            status='draft',
        )

        return Response(PostSerializer(post).data, status=status.HTTP_201_CREATED)
```

- [ ] **Step 6 : Créer les URLs**

```python
# backend/apps/posts/urls.py
from django.urls import path
from .views import PostListView, PostGenerateView

urlpatterns = [
    path('', PostListView.as_view(), name='posts-list'),
    path('generate/', PostGenerateView.as_view(), name='posts-generate'),
]
```

- [ ] **Step 7 : Lancer les tests**

```bash
cd backend && .venv/bin/python manage.py test apps.posts -v 2
```

Expected : `OK (4 tests)`

- [ ] **Step 8 : Commit**

```bash
git add backend/apps/posts/
git commit -m "feat: app posts — serializer, AI service, views, urls"
```

---

## Task 9 : Suite de tests complète + vérification finale

- [ ] **Step 1 : Lancer tous les tests**

```bash
cd backend && .venv/bin/python manage.py test apps -v 2
```

Expected : tous les tests passent

- [ ] **Step 2 : Vérifier manage.py check**

```bash
cd backend && .venv/bin/python manage.py check
```

Expected : `System check identified no issues (0 silenced).`

- [ ] **Step 3 : Commit final si modifs restantes**

```bash
git status
# Committer uniquement si des fichiers ont été modifiés
```

---

## Task 10 : Merge vers dev

- [ ] **Step 1 : Vérifier l'état du repo**

```bash
git log --oneline -8
git status
```

- [ ] **Step 2 : Merger**

```bash
git checkout dev
git merge refactor/django-backend --no-ff -m "feat: backend Django self-managed — simplejwt, Docker, sans Supabase"
git push origin dev
```

- [ ] **Step 3 : Vérifier**

```bash
git log --oneline -5
```
