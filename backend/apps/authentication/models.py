from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    PERSONA_CHOICES = [
        ('TRADER', 'Trader'),
        ('CREATEUR', 'Créateur'),
        ('JOURNALISTE', 'Journaliste'),
        ('POLITICIEN', 'Politicien'),
        ('PASSIONNE', 'Passionné'),
    ]
    TONE_CHOICES = [
        ('EXPERT', 'Expert'),
        ('ACCESSIBLE', 'Accessible'),
        ('DIRECT', 'Direct'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    persona = models.CharField(max_length=20, choices=PERSONA_CHOICES)
    style_prompt = models.TextField(blank=True, default='')
    style_prompt_manual = models.TextField(blank=True, default='')
    style_history = models.JSONField(default=list, blank=True)
    sector = models.CharField(max_length=100, blank=True, default='')
    tone = models.CharField(max_length=20, choices=TONE_CHOICES)
    email_digest = models.BooleanField(default=True)
    digest_hour = models.PositiveSmallIntegerField(default=7)
    weekly_digest = models.BooleanField(default=True)
    streak_current = models.PositiveIntegerField(default=0)
    streak_max = models.PositiveIntegerField(default=0)
    influence_score = models.PositiveIntegerField(default=0)
    influence_score_previous = models.PositiveIntegerField(default=0)
    influence_score_updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Profil {self.user} — {self.persona}"


class OTPCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_codes')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"OTP {self.user} — {self.code}"
