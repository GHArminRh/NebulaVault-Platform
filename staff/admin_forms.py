"""Cloudflare Turnstile protection for Django's staff/admin login."""

from django import forms
from django.conf import settings
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError

from accounts.turnstile import verify_turnstile


class AdminTurnstileAuthenticationForm(AdminAuthenticationForm):
    """Require a valid server-verified Turnstile token before admin authentication."""

    def clean(self):
        if getattr(settings, "TURNSTILE_ENABLED", True):
            site_key = getattr(settings, "TURNSTILE_SITE_KEY", "").strip()
            secret_key = getattr(settings, "TURNSTILE_SECRET_KEY", "").strip()
            token = (self.data.get("cf-turnstile-response") or "").strip()

            # Fail closed if Turnstile is enabled but not fully configured.
            if not site_key or not secret_key:
                raise ValidationError(
                    "تأیید امنیتی ورود ادمین پیکربندی نشده است. با مدیر سامانه تماس بگیرید."
                )
            if not token or not verify_turnstile(
                token,
                secret_key=secret_key,
                verify_url=getattr(
                    settings,
                    "TURNSTILE_VERIFY_URL",
                    "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                ),
            ):
                raise ValidationError(
                    "تأیید امنیتی ناموفق بود. لطفاً کپچا را تکمیل کنید و دوباره تلاش کنید."
                )

        return super().clean()
