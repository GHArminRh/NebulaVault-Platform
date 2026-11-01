"""Cloudflare Turnstile protection for Django's staff/admin login."""

from django import forms
from django.conf import settings
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError

from accounts.turnstile import verify_turnstile
from accounts.two_factor import decrypt_totp_secret, verify_totp


class AdminTurnstileAuthenticationForm(AdminAuthenticationForm):
    remember_me = forms.BooleanField(required=False, initial=True, label="Remember me")
    otp_token = forms.CharField(required=False, max_length=12, label="Authenticator code", widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "inputmode": "numeric", "placeholder": "6-digit code"}))

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

        cleaned = super().clean()
        staff_user = self.get_user()
        if staff_user.two_factor_enabled and not verify_totp(decrypt_totp_secret(staff_user.two_factor_secret), cleaned.get("otp_token")):
            self.add_error("otp_token", "The two-factor authentication code is invalid or missing.")
            return cleaned
        if self.request is not None:
            self.request.session.set_expiry(60 * 60 * 24 * 14 if cleaned.get("remember_me") else 0)
        return cleaned
