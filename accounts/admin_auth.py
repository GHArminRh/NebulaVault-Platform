"""Turnstile-protected authentication form for Django admin."""
from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from accounts.turnstile import verify_turnstile


class TurnstileAdminAuthenticationForm(AuthenticationForm):
    def clean(self):
        if getattr(settings, "TURNSTILE_ENABLED", True):
            token = (self.data.get("cf-turnstile-response") or "").strip()
            valid = verify_turnstile(
                token,
                secret_key=getattr(settings, "TURNSTILE_SECRET_KEY", ""),
                verify_url=getattr(
                    settings,
                    "TURNSTILE_VERIFY_URL",
                    "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                ),
            )
            if not valid:
                raise ValidationError("Security verification failed. Please complete the Cloudflare checkbox and try again.")
        return super().clean()
