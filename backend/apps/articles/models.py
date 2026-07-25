from django.conf import settings
from django.db import models
from apps.sources.models import Source


class Article(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='articles')
    title = models.TextField()
    content = models.TextField(blank=True, default='')
    url = models.TextField(blank=True, default='')
    score = models.FloatField(default=0.0)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Alert(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='alerts')
    keyword = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Alerte '{self.keyword}' — {self.user}"


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='notifications')
    keyword = models.CharField(max_length=100)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification '{self.keyword}' — {self.user}"


class DailyBriefing(models.Model):
    """Briefing flash Trader : jusqu'à 5 signaux (articles score > 70 des dernières
    24h), résumés en 3 lignes chacun. content = [{article_id, article_title, lines}, ...]."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='briefings')
    date = models.DateField()
    content = models.JSONField(default=list)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        unique_together = ['user', 'date']

    def __str__(self):
        return f"Briefing {self.user} — {self.date}"
