from django.db import models
from django.contrib.auth.models import User

from apps.authentication.models import Profile


class TopicPack(models.Model):
    """Ensemble de sources RSS pré-configurées proposées à l'onboarding selon
    le persona de l'utilisateur (SCRUM-27). sources = [{'name': ..., 'url': ...}, ...] —
    l'url peut être une page d'accueil (détectée automatiquement à l'activation,
    cf. apps.sources.services.detect_feed_urls) ou un flux RSS direct."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    persona = models.CharField(max_length=20, choices=Profile.PERSONA_CHOICES)
    sources = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.persona})"


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
