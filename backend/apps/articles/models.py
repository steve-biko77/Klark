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
