"""Cloudflare Turnstile protection for Django's staff/admin login."""

from django import forms
from django.conf import settings
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError

from accounts.turnstile import verify_turnstile
from accounts.two_factor import consume_recovery_code, decrypt_totp_secret, send_email_code, verify_email_challenge, verify_totp


class AdminTurnstileAuthenticationForm(AdminAuthenticationForm):
    """Require server-verified Turnstile and optional TOTP for staff sign-in."""

    remember_me = forms.BooleanField(required=False, initial=True, label="Remember me")
    otp_token = forms.CharField(required=False, max_length=12, label="Authenticator code", widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "inputmode": "numeric", "placeholder": "6-digit code"}))
    email_otp_token = forms.CharField(required=False, max_length=6, label="Email code")
    recovery_code = forms.CharField(required=False, max_length=16, label="Recovery code")


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
        if self.data.get("send_email_code") == "1":
            if not staff_user.email_two_factor_enabled:
                self.add_error(None, "Email two-factor authentication is not enabled for this account.")
            else:
                try:
                    sent = send_email_code(self.request, staff_user, purpose="login")
                except Exception:
                    sent = False
                if sent:
                    self.add_error(None, "A verification code was sent to your account email. It expires in 10 minutes.")
                else:
                    self.add_error(None, "The code could not be sent or was sent recently. Please try again shortly.")
            return cleaned

        if staff_user.two_factor_enabled or staff_user.email_two_factor_enabled:
            valid_factor = staff_user.two_factor_enabled and verify_totp(
                decrypt_totp_secret(staff_user.two_factor_secret), cleaned.get("otp_token")
            )
            if not valid_factor and staff_user.email_two_factor_enabled:
                valid_factor = verify_email_challenge(staff_user, cleaned.get("email_otp_token"), purpose="login")
            if not valid_factor:
                valid_factor = consume_recovery_code(staff_user, cleaned.get("recovery_code"))
            if not valid_factor:
                self.add_error("otp_token", "The two-factor or recovery code is invalid or missing.")
                return cleaned
        if self.request is not None:
            self.request.session.set_expiry(60 * 60 * 24 * 14 if cleaned.get("remember_me") else 0)
        return cleaned
