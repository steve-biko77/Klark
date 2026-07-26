from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    digest_hour = serializers.IntegerField(min_value=5, max_value=10, required=False)

    class Meta:
        model = Profile
        fields = ['persona', 'style_prompt', 'sector', 'tone', 'email_digest', 'digest_hour']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all(), message='Un compte existe déjà avec cet email.')]
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
        )
