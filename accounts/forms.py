from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Customer


class HumanCheckMixin:
    human_check = forms.BooleanField(
        required=True,
        error_messages={"required": "Please confirm that you are not a robot."},
        label="I'm not a robot",
    )


class NebulaAuthenticationForm(HumanCheckMixin, AuthenticationForm):
    username = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={"autocomplete": "username", "autofocus": True}),
    )

    def clean(self):
        # Keep Django's AuthenticationForm validation and authentication flow.
        # The configured CustomerAuthenticationBackend handles customer emails.
        return super().clean()


class RegisterForm(HumanCheckMixin, forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = Customer
        # Username is intentionally omitted: it is generated from the email.
        fields = ("email",)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Customer.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    @staticmethod
    def _username_from_email(email):
        base = email.rsplit("@", 1)[0].strip()
        if not base:
            raise ValidationError({"email": "The email address must have a username before @."})

        # Preserve the email's local-part exactly when available. If it is
        # already taken, add a numeric suffix without asking the user to choose.
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
            self.add_error("password2", "The two password fields didn't match.")
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
    username = forms.CharField(required=False, max_length=150, widget=forms.TextInput(attrs={"autocomplete": "username"}))

    class Meta:
        model = Customer
        fields = ("username", "first_name", "last_name", "email")
        widgets = {
            "username": forms.TextInput(attrs={"autocomplete": "username"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }

    def clean_username(self):
        username = self.cleaned_data["username"].strip() or self.instance.username
        if Customer.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise ValidationError("This username is already in use. Please choose another.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Customer.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("An account with this email already exists.")
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
