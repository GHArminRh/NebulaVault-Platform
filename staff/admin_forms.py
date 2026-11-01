"""Cloudflare Turnstile protection and staged two-factor authentication for staff login."""

import time

from django import forms
from django.conf import settings
from django.contrib.admin.forms import AdminAuthenticationForm

from accounts.turnstile import verify_turnstile
from accounts.two_factor import (
    consume_recovery_code,
    decrypt_totp_secret,
    send_email_code,
    verify_email_challenge,
    verify_totp,
)
from staff.models import StaffUser


class AdminTurnstileAuthenticationForm(AdminAuthenticationForm):
    remember_me = forms.BooleanField(required=False, initial=True, label="Remember me")
    otp_token = forms.CharField(required=False, max_length=12, label="Authenticator code", widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "inputmode": "numeric"}))
    email_otp_token = forms.CharField(required=False, max_length=6, label="Email code")
    recovery_code = forms.CharField(required=False, max_length=16, label="Recovery code")
    two_factor_method = forms.ChoiceField(required=False, choices=(), label="Verification method")

    PENDING_SESSION_KEY = "staff_two_factor_pending"
    CHALLENGE_TTL_SECONDS = 300

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.two_factor_required = False
        self.two_factor_methods = []
        self._pending_staff_user = None
        pending = request.session.get(self.PENDING_SESSION_KEY) if request else None
        if pending and time.time() - pending.get("created_at", 0) <= self.CHALLENGE_TTL_SECONDS:
            staff_user = StaffUser.objects.filter(
                pk=pending.get("user_id"), is_active=True, is_staff=True
            ).first()
            if staff_user and (staff_user.two_factor_enabled or staff_user.email_two_factor_enabled or staff_user.recovery_codes):
                self._pending_staff_user = staff_user
                self.two_factor_required = True
                self._configure_methods(staff_user)
                self.fields["username"].required = False
                self.fields["password"].required = False
        elif pending and request:
            request.session.pop(self.PENDING_SESSION_KEY, None)

    def _configure_methods(self, staff_user):
        methods = []
        if staff_user.two_factor_enabled:
            methods.append(("authenticator", "Authenticator app"))
        if staff_user.email_two_factor_enabled:
            methods.append(("email", "Email verification code"))
        if staff_user.recovery_codes:
            methods.append(("recovery", "Recovery code"))
        self.two_factor_methods = methods
        self.fields["two_factor_method"].choices = methods

    def _apply_remember_preference(self, remember):
        if self.request is not None:
            self.request.session.set_expiry(60 * 60 * 24 * 14 if remember else 0)

    def clean(self):
        if self._pending_staff_user is not None:
            staff_user = self._pending_staff_user
            method = self.cleaned_data.get("two_factor_method") or ""
            if method == "email" and self.data.get("send_email_code") == "1":
                try:
                    sent = send_email_code(self.request, staff_user, purpose="login")
                except Exception:
                    sent = False
                if sent:
                    self.add_error(None, "A verification code was sent to your email and expires in 10 minutes.")
                else:
                    self.add_error(None, "The code could not be sent or was sent recently. Please try again shortly.")
                return self.cleaned_data

            valid = False
            if method == "authenticator" and staff_user.two_factor_enabled:
                valid = verify_totp(decrypt_totp_secret(staff_user.two_factor_secret), self.cleaned_data.get("otp_token"))
            elif method == "email" and staff_user.email_two_factor_enabled:
                valid = verify_email_challenge(staff_user, self.cleaned_data.get("email_otp_token"), purpose="login")
            elif method == "recovery" and staff_user.recovery_codes:
                valid = consume_recovery_code(staff_user, self.cleaned_data.get("recovery_code"))

            if not valid:
                self.add_error(None, "The selected verification method or code is invalid. Please try again.")
                return self.cleaned_data

            pending = self.request.session.pop(self.PENDING_SESSION_KEY, {})
            self._apply_remember_preference(pending.get("remember_me", True))
            self.user_cache = staff_user
            return self.cleaned_data

        if getattr(settings, "TURNSTILE_ENABLED", True):
            site_key = getattr(settings, "TURNSTILE_SITE_KEY", "").strip()
            secret_key = getattr(settings, "TURNSTILE_SECRET_KEY", "").strip()
            token = (self.data.get("cf-turnstile-response") or "").strip()
            if not site_key or not secret_key:
                raise forms.ValidationError(
                    "Admin security verification is not configured. Contact the system administrator."
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
                raise forms.ValidationError(
                    "Security verification failed. Please complete the CAPTCHA and try again."
                )

        cleaned = super().clean()
        staff_user = self.get_user()
        if staff_user.two_factor_enabled or staff_user.email_two_factor_enabled or staff_user.recovery_codes:
            self._configure_methods(staff_user)
            self.two_factor_required = True
            self.request.session[self.PENDING_SESSION_KEY] = {
                "user_id": str(staff_user.pk),
                "created_at": time.time(),
                "remember_me": bool(cleaned.get("remember_me", True)),
            }
            self.add_error(None, "Password accepted. Choose a second-factor method to continue.")
            return self.cleaned_data

        self._apply_remember_preference(cleaned.get("remember_me", True))
        return cleaned
