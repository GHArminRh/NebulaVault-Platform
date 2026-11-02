import time
from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

from .models import Customer
from .turnstile import verify_turnstile
from .two_factor import consume_recovery_code, decrypt_totp_secret, send_email_code, verify_email_challenge, verify_totp


class HumanCheckMixin:
    turnstile_action = "customer_auth"
    # Compatibility only; this hidden value is never trusted as proof of a human.
    human_check = forms.BooleanField(required=False, widget=forms.HiddenInput())

    def clean(self):
        # Verify Turnstile before Django's authentication clean() so inactive
        # accounts can still be routed to verification only after passing CAPTCHA.
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
                expected_action=self.turnstile_action,
            )
            if not valid:
                self.turnstile_error = True
                raise ValidationError(
                    "تأیید امنیتی ناموفق بود. لطفاً کپچا را تکمیل کنید و دوباره تلاش کنید."
                )
            self.cleaned_data["turnstile_verified"] = True
        else:
            # Tests/local development may explicitly disable Turnstile.
            self.cleaned_data["turnstile_verified"] = True
        return super().clean()


class NebulaAuthenticationForm(HumanCheckMixin, AuthenticationForm):
    turnstile_action = "customer_login"
    remember_me = forms.BooleanField(required=False, initial=True, label="مرا به خاطر بسپار")
    otp_token = forms.CharField(required=False, max_length=12, label="کد برنامه احراز هویت", widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "inputmode": "numeric"}))
    email_otp_token = forms.CharField(required=False, max_length=6, label="کد ایمیل")
    recovery_code = forms.CharField(required=False, max_length=16, label="کد بازیابی")
    two_factor_method = forms.ChoiceField(required=False, choices=(), label="روش تأیید")
    username = forms.EmailField(label="نشانی ایمیل", widget=forms.EmailInput(attrs={"autocomplete": "username", "autofocus": True}))

    PENDING_SESSION_KEY = "customer_two_factor_pending"
    CHALLENGE_TTL_SECONDS = 300

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.two_factor_required = False
        self.two_factor_methods = []
        self._pending_customer = None
        pending = self.request.session.get(self.PENDING_SESSION_KEY) if self.request else None
        if pending and time.time() - pending.get("created_at", 0) <= self.CHALLENGE_TTL_SECONDS:
            customer = Customer.objects.filter(pk=pending.get("user_id"), is_active=True, is_banned=False).first()
            if customer and (customer.two_factor_enabled or customer.email_two_factor_enabled or customer.recovery_codes):
                self._pending_customer = customer
                self.two_factor_required = True
                self._configure_methods(customer)
                self.fields["username"].required = False
                self.fields["password"].required = False
            elif self.request:
                self.request.session.pop(self.PENDING_SESSION_KEY, None)
        elif pending and self.request:
            self.request.session.pop(self.PENDING_SESSION_KEY, None)

    def _configure_methods(self, customer):
        methods = []
        if customer.two_factor_enabled:
            methods.append(("authenticator", "برنامه احراز هویت"))
        if customer.email_two_factor_enabled:
            methods.append(("email", "کد ایمیل"))
        if customer.recovery_codes:
            methods.append(("recovery", "کد بازیابی"))
        self.two_factor_methods = methods
        self.fields["two_factor_method"].choices = methods

    def _apply_remember_preference(self, remember):
        if self.request is not None:
            self.request.session.set_expiry(60 * 60 * 24 * 14 if remember else 0)

    def clean(self):
        if self._pending_customer is not None:
            customer = self._pending_customer
            self.cleaned_data["turnstile_verified"] = True
            method = self.cleaned_data.get("two_factor_method") or ""
            if method == "email" and self.data.get("send_email_code") == "1":
                try:
                    sent = send_email_code(self.request, customer, purpose="login")
                except Exception:
                    sent = False
                if sent:
                    self.add_error(None, "کد تأیید به ایمیل شما ارسال شد و تا ۱۰ دقیقه اعتبار دارد.")
                else:
                    self.add_error(None, "ارسال کد ممکن نشد یا اخیراً کدی ارسال شده است؛ کمی بعد دوباره تلاش کنید.")
                return self.cleaned_data

            valid = False
            if method == "authenticator" and customer.two_factor_enabled:
                valid = verify_totp(decrypt_totp_secret(customer.two_factor_secret), self.cleaned_data.get("otp_token"))
            elif method == "email" and customer.email_two_factor_enabled:
                valid = verify_email_challenge(customer, self.cleaned_data.get("email_otp_token"), purpose="login")
            elif method == "recovery" and customer.recovery_codes:
                valid = consume_recovery_code(customer, self.cleaned_data.get("recovery_code"))

            if not valid:
                self.add_error(None, "روش انتخاب‌شده یا کد تأیید معتبر نیست. دوباره تلاش کنید.")
                return self.cleaned_data

            pending = self.request.session.pop(self.PENDING_SESSION_KEY, {})
            self._apply_remember_preference(pending.get("remember_me", True))
            customer.backend = "accounts.backends.CustomerAuthenticationBackend"
            self.user_cache = customer
            return self.cleaned_data

        cleaned = super().clean()
        customer = self.get_user()
        if customer.two_factor_enabled or customer.email_two_factor_enabled or customer.recovery_codes:
            self._configure_methods(customer)
            self.two_factor_required = True
            self.request.session[self.PENDING_SESSION_KEY] = {
                "user_id": str(customer.pk),
                "created_at": time.time(),
                "remember_me": bool(cleaned.get("remember_me", True)),
            }
            self.add_error(None, "رمز عبور تأیید شد. اکنون روش تأیید دومرحله‌ای را انتخاب کنید.")
            return self.cleaned_data

        self._apply_remember_preference(cleaned.get("remember_me", True))
        return cleaned


class RegisterForm(HumanCheckMixin, forms.ModelForm):
    turnstile_action = "customer_register"
    password1 = forms.CharField(
        label="رمز عبور",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="تکرار رمز عبور",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = Customer
        fields = ("email",)

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        local_part, separator, domain = email.rpartition("@")
        if separator:
            email = f"{local_part}@{domain.lower()}"
        if Customer.objects.filter(email__iexact=email).exists():
            raise ValidationError("حسابی با این نشانی ایمیل از قبل وجود دارد.")
        return email

    @staticmethod
    def _username_from_email(email):
        base = email.rsplit("@", 1)[0].strip()
        if not base:
            raise ValidationError({"email": "نشانی ایمیل باید پیش از علامت @ نام کاربری داشته باشد."})
        candidate = base[:150]
        suffix = 2
        while Customer.objects.filter(username__iexact=candidate).exists():
            tail = str(suffix)
            candidate = f"{base[:150 - len(tail)]}{tail}"
            suffix += 1
        return candidate

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "رمزهای عبور واردشده یکسان نیستند.")
        if p1:
            try:
                validate_password(p1, self.instance)
            except ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned

    def save(self, commit=True):
        customer = super().save(commit=False)
        customer.email = self.cleaned_data["email"]
        customer.username = self._username_from_email(customer.email)
        customer.set_password(self.cleaned_data["password1"])
        if commit:
            customer.save()
        return customer


class AccountProfileForm(forms.ModelForm):
    username = forms.CharField(label="نام کاربری", required=False, max_length=150, widget=forms.TextInput(attrs={"autocomplete": "username"}))

    class Meta:
        model = Customer
        fields = ("username", "first_name", "last_name", "email", "avatar")
        labels = {
            "username": "نام کاربری",
            "first_name": "نام",
            "last_name": "نام خانوادگی",
            "email": "نشانی ایمیل",
            "avatar": "تصویر نمایه",
        }
        widgets = {
            "username": forms.TextInput(attrs={"autocomplete": "username"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "avatar": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        }

    def clean_username(self):
        username = self.cleaned_data["username"].strip() or self.instance.username
        if Customer.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise ValidationError("این نام کاربری قبلاً استفاده شده است. نام دیگری انتخاب کنید.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Customer.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("حسابی با این نشانی ایمیل از قبل وجود دارد.")
        return email


class AccountPasswordChangeForm(PasswordChangeForm):
    pass


class AccountSetPasswordForm(SetPasswordForm):
    pass


class AccountPasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        for customer in Customer.objects.filter(email__iexact=email.strip().lower(), is_active=True):
            if customer.has_usable_password():
                yield customer


class VerificationResendForm(forms.Form):
    email = forms.EmailField(
        label="نشانی ایمیل",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "you@example.com"}),
    )


from staff.models import StaffUser


class StaffAccountProfileForm(forms.ModelForm):
    class Meta:
        model = StaffUser
        fields = ("first_name", "last_name", "email", "avatar")
        labels = {
            "first_name": "First name",
            "last_name": "Last name",
            "email": "Email address",
            "avatar": "Profile photo",
        }
        widgets = {
            "avatar": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        }
