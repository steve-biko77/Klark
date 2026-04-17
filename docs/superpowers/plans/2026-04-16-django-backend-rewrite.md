# Django Backend Rewrite — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Réécrire le backend Klark de FastAPI vers Django + DRF en gardant les mêmes endpoints, en utilisant les commandes CLI Django pour scaffolder, et en connectant Django à la base PostgreSQL Supabase existante.

**Architecture:** Architecture en couches avec une app Django par domaine métier (`sources`, `articles`, `posts`), une app `authentication` pour la validation des JWT Supabase, et un projet `config/` central. Les modèles sont `managed=True` avec `--fake-initial` pour les tables Supabase existantes.

**Tech Stack:** Django 5.2, Django REST Framework 3.17, PyJWT, Supabase Python SDK, dj-database-url, python-decouple, feedparser, anthropic SDK

---

## Structure des fichiers

```
backend/
  manage.py                          ← généré par startproject
  config/
    __init__.py                      ← généré
    settings.py                      ← modifié : DRF, CORS, DB, auth
    urls.py                          ← modifié : inclut les urls des apps
    wsgi.py                          ← généré
    asgi.py                          ← généré
  apps/
    __init__.py                      ← créé manuellement
    authentication/
      __init__.py                    ← généré
      apps.py                        ← modifié : name = 'apps.authentication'
      backends.py                    ← créé : SupabaseUser + SupabaseAuthentication
    sources/
      __init__.py                    ← généré
      apps.py                        ← modifié : name = 'apps.sources'
      models.py                      ← modifié : Source model
      serializers.py                 ← créé
      services.py                    ← créé : scraper_service
      views.py                       ← modifié
      urls.py                        ← créé
    articles/
      __init__.py                    ← généré
      apps.py                        ← modifié : name = 'apps.articles'
      models.py                      ← modifié : Article model
      serializers.py                 ← créé
      views.py                       ← modifié
      urls.py                        ← créé
    posts/
      __init__.py                    ← généré
      apps.py                        ← modifié : name = 'apps.posts'
      models.py                      ← modifié : Post model
      serializers.py                 ← créé
      services.py                    ← créé : ai_service
      views.py                       ← modifié
      urls.py                        ← créé
```

---

## Task 1 : Bootstrap du projet Django (CLI uniquement)

**Files:**
- Create: `backend/manage.py` (généré)
- Create: `backend/config/` (généré)
- Create: `backend/apps/__init__.py`
- Create: `backend/apps/authentication/` (généré)
- Create: `backend/apps/sources/` (généré)
- Create: `backend/apps/articles/` (généré)
- Create: `backend/apps/posts/` (généré)

- [ ] **Step 1 : Créer le projet Django**

```bash
cd backend && .venv/bin/django-admin startproject config .
```

Expected : création de `manage.py`, `config/__init__.py`, `config/settings.py`, `config/urls.py`, `config/wsgi.py`, `config/asgi.py`

- [ ] **Step 2 : Créer le dossier apps et son __init__.py**

```bash
mkdir -p backend/apps && touch backend/apps/__init__.py
```

- [ ] **Step 3 : Créer les dossiers pour chaque app puis scaffolder**

```bash
cd backend
mkdir -p apps/authentication apps/sources apps/articles apps/posts
.venv/bin/python manage.py startapp authentication apps/authentication
.venv/bin/python manage.py startapp sources apps/sources
.venv/bin/python manage.py startapp articles apps/articles
.venv/bin/python manage.py startapp posts apps/posts
```

Expected : chaque dossier contient `__init__.py`, `apps.py`, `models.py`, `views.py`, `tests.py`, `admin.py`, `migrations/`

- [ ] **Step 4 : Commit**

```bash
git add backend/
git commit -m "chore: bootstrap Django project + apps via CLI"
```

---

## Task 2 : Configuration de settings.py

**Files:**
- Modify: `backend/config/settings.py`

- [ ] **Step 1 : Créer le fichier .env backend** (si pas déjà présent)

Créer `backend/.env` avec ce contenu minimal (à remplir avec les vraies valeurs) :

```env
SECRET_KEY=django-insecure-change-me-in-production
DEBUG=True
DATABASE_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
ANTHROPIC_API_KEY=your_anthropic_key
ALLOWED_HOSTS=localhost,127.0.0.1
```

- [ ] **Step 2 : Réécrire settings.py**

```python
# backend/config/settings.py
from pathlib import Path
from decouple import config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'rest_framework',
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

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL')
    )
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
        'apps.authentication.backends.SupabaseAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# CORS
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
]
CORS_ALLOW_CREDENTIALS = True

# Supabase
SUPABASE_URL = config('SUPABASE_URL')
SUPABASE_SERVICE_KEY = config('SUPABASE_SERVICE_KEY')

# Anthropic
ANTHROPIC_API_KEY = config('ANTHROPIC_API_KEY')
```

- [ ] **Step 3 : Vérifier que Django démarre sans erreur**

```bash
cd backend && .venv/bin/python manage.py check
```

Expected : `System check identified no issues (0 silenced).`

- [ ] **Step 4 : Commit**

```bash
git add backend/config/settings.py backend/.env.example
git commit -m "feat: configure Django settings (DRF, CORS, DB, Supabase)"
```

---

## Task 3 : App authentication — JWT Supabase

**Files:**
- Modify: `backend/apps/authentication/apps.py`
- Create: `backend/apps/authentication/backends.py`

- [ ] **Step 1 : Corriger le name dans apps.py**

```python
# backend/apps/authentication/apps.py
from django.apps import AppConfig

class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.authentication'
```

- [ ] **Step 2 : Écrire le test d'abord**

```python
# backend/apps/authentication/tests.py
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
```

- [ ] **Step 3 : Lancer le test pour vérifier qu'il échoue**

```bash
cd backend && .venv/bin/python manage.py test apps.authentication -v 2
```

Expected : `ImportError: cannot import name 'SupabaseAuthentication'`

- [ ] **Step 4 : Implémenter backends.py**

```python
# backend/apps/authentication/backends.py
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
```

- [ ] **Step 5 : Lancer les tests pour vérifier qu'ils passent**

```bash
cd backend && .venv/bin/python manage.py test apps.authentication -v 2
```

Expected : `OK (3 tests)`

- [ ] **Step 6 : Commit**

```bash
git add backend/apps/authentication/
git commit -m "feat: Supabase JWT authentication backend"
```

---

## Task 4 : Modèles Django (sources, articles, posts)

**Files:**
- Modify: `backend/apps/sources/apps.py`, `backend/apps/sources/models.py`
- Modify: `backend/apps/articles/apps.py`, `backend/apps/articles/models.py`
- Modify: `backend/apps/posts/apps.py`, `backend/apps/posts/models.py`

- [ ] **Step 1 : Corriger le name dans les apps.py des 3 apps**

```python
# backend/apps/sources/apps.py
from django.apps import AppConfig

class SourcesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sources'
```

```python
# backend/apps/articles/apps.py
from django.apps import AppConfig

class ArticlesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.articles'
```

```python
# backend/apps/posts/apps.py
from django.apps import AppConfig

class PostsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.posts'
```

- [ ] **Step 2 : Modèle Source**

```python
# backend/apps/sources/models.py
import uuid
from django.db import models


class Source(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    url = models.TextField()
    name = models.TextField(blank=True, default='')
    type = models.TextField(default='rss')
    status = models.TextField(default='pending')
    last_crawled = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sources'
        ordering = ['-created_at']
```

- [ ] **Step 3 : Modèle Article**

```python
# backend/apps/articles/models.py
import uuid
from django.db import models


class Article(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_id = models.UUIDField()
    title = models.TextField()
    content = models.TextField(blank=True, default='')
    url = models.TextField(blank=True, default='')
    score = models.FloatField(default=0.0)
    published_at = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'articles'
        ordering = ['-created_at']
```

- [ ] **Step 4 : Modèle Post**

```python
# backend/apps/posts/models.py
import uuid
from django.db import models


class Post(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    article_id = models.UUIDField(null=True, blank=True)
    content = models.TextField()
    platform = models.TextField(default='linkedin')
    status = models.TextField(default='draft')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'posts'
        ordering = ['-created_at']
```

- [ ] **Step 5 : Commit**

```bash
git add backend/apps/
git commit -m "feat: Django models pour sources, articles, posts"
```

---

## Task 5 : Migrations initiales + fake-initial

**Files:**
- Create: `backend/apps/sources/migrations/0001_initial.py` (généré)
- Create: `backend/apps/articles/migrations/0001_initial.py` (généré)
- Create: `backend/apps/posts/migrations/0001_initial.py` (généré)

> **Prérequis :** Le fichier `backend/.env` doit contenir un `DATABASE_URL` valide pointant vers Supabase.

- [ ] **Step 1 : Générer les migrations**

```bash
cd backend && .venv/bin/python manage.py makemigrations
```

Expected :
```
Migrations for 'sources':
  apps/sources/migrations/0001_initial.py
    - Create model Source
Migrations for 'articles':
  apps/articles/migrations/0001_initial.py
    - Create model Article
Migrations for 'posts':
  apps/posts/migrations/0001_initial.py
    - Create model Post
```

- [ ] **Step 2 : Appliquer avec --fake-initial (tables déjà dans Supabase)**

```bash
cd backend && .venv/bin/python manage.py migrate --fake-initial
```

Expected : chaque migration est marquée comme `OK` sans recréer les tables existantes. Django crée uniquement sa propre table `django_migrations`.

- [ ] **Step 3 : Vérifier l'état des migrations**

```bash
cd backend && .venv/bin/python manage.py showmigrations
```

Expected : toutes les migrations `apps.sources`, `apps.articles`, `apps.posts` sont cochées `[X]`.

- [ ] **Step 4 : Commit**

```bash
git add backend/apps/sources/migrations/ backend/apps/articles/migrations/ backend/apps/posts/migrations/
git commit -m "feat: migrations initiales Django (fake-initial sur tables Supabase)"
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
from unittest.mock import patch, MagicMock
from rest_framework.test import APITestCase
from rest_framework import status
from apps.authentication.backends import SupabaseUser
import uuid


class SourcesViewTest(APITestCase):

    def _auth(self, user_id=None):
        uid = user_id or str(uuid.uuid4())
        self.client.force_authenticate(user=SupabaseUser(uid))
        return uid

    def test_list_sources_unauthenticated(self):
        response = self.client.get('/sources/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_sources_returns_200(self):
        self._auth()
        response = self.client.get('/sources/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_create_source(self):
        self._auth()
        data = {'url': 'https://example.com/rss', 'name': 'Test Feed'}
        response = self.client.post('/sources/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['url'], data['url'])

    @patch('apps.sources.views.scrape_source')
    def test_scrape_source(self, mock_scrape):
        uid = self._auth()
        mock_scrape.return_value = {'articles_added': 5, 'total_found': 10}

        from apps.sources.models import Source
        source = Source.objects.create(user_id=uid, url='https://example.com/rss')

        response = self.client.post(f'/sources/{source.id}/scrape/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['articles_added'], 5)
```

- [ ] **Step 2 : Lancer les tests pour vérifier qu'ils échouent**

```bash
cd backend && .venv/bin/python manage.py test apps.sources -v 2
```

Expected : `ImportError` ou `404` — les URLs n'existent pas encore.

- [ ] **Step 3 : Créer le serializer**

```python
# backend/apps/sources/serializers.py
from rest_framework import serializers
from .models import Source


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = ['id', 'url', 'name', 'type', 'status', 'last_crawled', 'created_at']
        read_only_fields = ['id', 'status', 'last_crawled', 'created_at']
```

- [ ] **Step 4 : Créer le service scraper**

```python
# backend/apps/sources/services.py
import feedparser
from datetime import datetime, timezone
from apps.articles.models import Article
from .models import Source


def scrape_source(source_id: str, url: str, user_id: str) -> dict:
    feed = feedparser.parse(url)

    if feed.bozo:
        Source.objects.filter(id=source_id).update(status='error')
        return {'error': 'Flux RSS invalide', 'articles_added': 0}

    articles_added = 0
    for entry in feed.entries[:10]:
        link = entry.get('link', '')
        if Article.objects.filter(source_id=source_id, url=link).exists():
            continue

        Article.objects.create(
            source_id=source_id,
            title=entry.get('title', 'Sans titre'),
            content=entry.get('summary', entry.get('description', '')),
            url=link,
            score=0.0,
            published_at=entry.get('published', None),
        )
        articles_added += 1

    Source.objects.filter(id=source_id).update(
        status='active',
        last_crawled=datetime.now(timezone.utc)
    )

    return {
        'source_id': source_id,
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
        sources = Source.objects.filter(user_id=request.user.user_id)
        serializer = SourceSerializer(sources, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = SourceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user_id=request.user.user_id, type='rss', status='pending')
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SourceScrapeView(APIView):

    def post(self, request, source_id):
        source = get_object_or_404(Source, id=source_id, user_id=request.user.user_id)
        result = scrape_source(
            source_id=str(source.id),
            url=source.url,
            user_id=str(request.user.user_id),
        )
        return Response(result)
```

- [ ] **Step 6 : Créer les urls**

```python
# backend/apps/sources/urls.py
from django.urls import path
from .views import SourceListCreateView, SourceScrapeView

urlpatterns = [
    path('', SourceListCreateView.as_view(), name='sources-list'),
    path('<uuid:source_id>/scrape/', SourceScrapeView.as_view(), name='source-scrape'),
]
```

- [ ] **Step 7 : Lancer les tests**

```bash
cd backend && .venv/bin/python manage.py test apps.sources -v 2
```

Expected : `OK (4 tests)` — (les tests d'intégration DB peuvent nécessiter le `.env`)

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
from rest_framework.test import APITestCase
from rest_framework import status
from apps.authentication.backends import SupabaseUser
from apps.sources.models import Source
from apps.articles.models import Article
import uuid


class ArticlesViewTest(APITestCase):

    def _auth(self, user_id=None):
        uid = user_id or str(uuid.uuid4())
        self.client.force_authenticate(user=SupabaseUser(uid))
        return uid

    def test_list_articles_unauthenticated(self):
        response = self.client.get('/articles/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_articles_returns_only_user_articles(self):
        uid = self._auth()
        source = Source.objects.create(user_id=uid, url='https://example.com/rss')
        Article.objects.create(source_id=source.id, title='Mon article', url='https://a.com')

        other_source = Source.objects.create(user_id=uuid.uuid4(), url='https://other.com/rss')
        Article.objects.create(source_id=other_source.id, title='Autre article', url='https://b.com')

        response = self.client.get('/articles/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Mon article')
```

- [ ] **Step 2 : Lancer pour vérifier l'échec**

```bash
cd backend && .venv/bin/python manage.py test apps.articles -v 2
```

Expected : `404` ou `ImportError` — URLs pas encore câblées.

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
from apps.sources.models import Source


class ArticleListView(APIView):

    def get(self, request):
        source_ids = Source.objects.filter(
            user_id=request.user.user_id
        ).values_list('id', flat=True)

        if not source_ids:
            return Response([])

        articles = Article.objects.filter(source_id__in=source_ids)
        serializer = ArticleSerializer(articles, many=True)
        return Response(serializer.data)
```

- [ ] **Step 5 : Créer les urls**

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

Expected : `OK (2 tests)`

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
from rest_framework.test import APITestCase
from rest_framework import status
from apps.authentication.backends import SupabaseUser
from apps.sources.models import Source
from apps.articles.models import Article
from apps.posts.models import Post
import uuid


class PostsViewTest(APITestCase):

    def _auth(self, user_id=None):
        uid = user_id or str(uuid.uuid4())
        self.client.force_authenticate(user=SupabaseUser(uid))
        return uid

    def test_list_posts_unauthenticated(self):
        response = self.client.get('/posts/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_posts_returns_only_user_posts(self):
        uid = self._auth()
        Post.objects.create(user_id=uid, content='Mon post', platform='linkedin')
        Post.objects.create(user_id=uuid.uuid4(), content='Autre post', platform='twitter')

        response = self.client.get('/posts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    @patch('apps.posts.views.generate_post')
    def test_generate_post(self, mock_generate):
        uid = self._auth()
        mock_generate.return_value = 'Contenu généré par IA'

        source = Source.objects.create(user_id=uid, url='https://example.com/rss')
        article = Article.objects.create(source_id=source.id, title='Titre', content='Contenu', url='https://a.com')

        data = {'article_id': str(article.id), 'platform': 'linkedin'}
        response = self.client.post('/posts/generate/', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], 'Contenu généré par IA')
        self.assertEqual(response.data['platform'], 'linkedin')

    @patch('apps.posts.views.generate_post')
    def test_generate_post_article_not_found(self, mock_generate):
        self._auth()
        data = {'article_id': str(uuid.uuid4()), 'platform': 'linkedin'}
        response = self.client.post('/posts/generate/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
```

- [ ] **Step 2 : Lancer pour vérifier l'échec**

```bash
cd backend && .venv/bin/python manage.py test apps.posts -v 2
```

Expected : `ImportError` ou `404`.

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
    style = f'\nStyle de l\'auteur : {style_prompt}' if style_prompt else ''

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
        posts = Post.objects.filter(user_id=request.user.user_id)
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data)


class PostGenerateView(APIView):

    def post(self, request):
        article_id = request.data.get('article_id')
        platform = request.data.get('platform', 'linkedin')

        article = get_object_or_404(Article, id=article_id)

        content = generate_post(
            article_title=article.title,
            article_content=article.content or '',
            platform=platform,
        )

        post = Post.objects.create(
            user_id=request.user.user_id,
            article_id=article.id,
            content=content,
            platform=platform,
            status='draft',
        )

        serializer = PostSerializer(post)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
```

- [ ] **Step 6 : Créer les urls**

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

## Task 9 : URLs racine + endpoint /health/

**Files:**
- Modify: `backend/config/urls.py`

- [ ] **Step 1 : Écrire les urls principales**

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
    path('sources/', include('apps.sources.urls')),
    path('articles/', include('apps.articles.urls')),
    path('posts/', include('apps.posts.urls')),
]
```

- [ ] **Step 2 : Vérifier la cohérence des URLs**

```bash
cd backend && .venv/bin/python manage.py show_urls 2>/dev/null || .venv/bin/python manage.py check
```

Expected : `System check identified no issues (0 silenced).`

- [ ] **Step 3 : Lancer tous les tests**

```bash
cd backend && .venv/bin/python manage.py test apps -v 2
```

Expected : tous les tests passent (`OK`)

- [ ] **Step 4 : Démarrer le serveur et tester /health/**

```bash
cd backend && .venv/bin/python manage.py runserver
```

Dans un autre terminal :
```bash
curl http://localhost:8000/health/
```
Expected : `{"status": "ok", "service": "klark-api"}`

- [ ] **Step 5 : Commit**

```bash
git add backend/config/urls.py
git commit -m "feat: config/urls.py — câblage de toutes les routes + /health/"
```

---

## Task 10 : Merge vers dev

- [ ] **Step 1 : Lancer la suite de tests complète**

```bash
cd backend && .venv/bin/python manage.py test apps -v 2
```

Expected : tous les tests passent.

- [ ] **Step 2 : Merger refactor/django-backend vers dev**

```bash
git checkout dev
git merge refactor/django-backend --no-ff -m "feat: refactor backend FastAPI → Django + DRF"
git push origin dev
```

- [ ] **Step 3 : Vérifier l'état du repo**

```bash
git log --oneline -5
git status
```

Expected : branche `dev` à jour, working tree propre.
