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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.platform} — {self.content[:50]}"
