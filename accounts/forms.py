from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

from .models import Customer
from .turnstile import verify_turnstile
from .two_factor import decrypt_totp_secret, verify_totp


class HumanCheckMixin:
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
    remember_me = forms.BooleanField(required=False, initial=True, label="مرا به خاطر بسپار")
    otp_token = forms.CharField(required=False, max_length=12, label="کد تأیید دومرحله‌ای", widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "inputmode": "numeric", "placeholder": "کد ۶ رقمی برنامه احراز هویت"}))
    username = forms.EmailField(
        label="نشانی ایمیل",
        widget=forms.EmailInput(attrs={"autocomplete": "username", "autofocus": True}),
    )

    def clean(self):
        try:
            # Keep Django's normal authentication flow for active customers.
            cleaned = super().clean()
        except ValidationError:
            # Only reveal account state after password and Turnstile both pass.
            email = (self.data.get(self.add_prefix("username")) or "").strip()
            password = self.data.get(self.add_prefix("password")) or ""
            customer = Customer.objects.filter(email__iexact=email).first()
            if self.cleaned_data.get("turnstile_verified") and customer and password and customer.check_password(password):
                if customer.is_banned:
                    self.banned_account = True
                elif not customer.is_active:
                    self.inactive_email = customer.email
            raise
        customer = self.get_user()
        if customer.two_factor_enabled and not verify_totp(decrypt_totp_secret(customer.two_factor_secret), self.cleaned_data.get("otp_token")):
            self.add_error("otp_token", "کد تأیید دومرحله‌ای نامعتبر است یا وارد نشده است.")
            return self.cleaned_data
        if self.request is not None:
            self.request.session.set_expiry(60 * 60 * 24 * 14 if self.cleaned_data.get("remember_me") else 0)
        return cleaned


class RegisterForm(HumanCheckMixin, forms.ModelForm):
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
