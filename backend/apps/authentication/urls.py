from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView,
    LoginView,
    VerifyOTPView,
    ResendOTPView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('verify-otp/', VerifyOTPView.as_view(), name='auth-verify-otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='auth-resend-otp'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='auth-password-reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='auth-password-reset-confirm'),
]
