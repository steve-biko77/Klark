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
