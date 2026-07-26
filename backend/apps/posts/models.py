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
    ('scheduled', 'Planifié'),
    ('published', 'Publié'),
    ('failed', 'Échoué'),
]


class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    article = models.ForeignKey(Article, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    content = models.TextField()
    platform = models.TextField(choices=PLATFORM_CHOICES, default='linkedin')
    status = models.TextField(choices=STATUS_CHOICES, default='draft')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    post_urn = models.TextField(null=True, blank=True)
    celery_task_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.platform} — {self.content[:50]}"


class Analytics(models.Model):
    """Métriques d'engagement LinkedIn d'un post publié (SCRUM-36). Une ligne par
    collecte (pas de OneToOne) pour permettre la courbe d'évolution 30 jours."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='analytics')
    likes = models.PositiveIntegerField(default=0)
    views = models.PositiveIntegerField(default=0)
    shares = models.PositiveIntegerField(default=0)
    comments = models.PositiveIntegerField(default=0)
    engagement_rate = models.FloatField(default=0.0)
    collected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-collected_at']
        verbose_name_plural = 'Analytics'

    def __str__(self):
        return f"Analytics {self.post_id} — {self.collected_at:%Y-%m-%d}"


class LinkedInToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='linkedin_token')
    access_token = models.TextField()
    token_type = models.TextField(default='Bearer')
    expires_at = models.DateTimeField()
    refresh_token = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"LinkedIn token — {self.user.username}"
