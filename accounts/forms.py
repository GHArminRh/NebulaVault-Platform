from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, PasswordResetForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import Customer


class HumanCheckMixin:
    human_check = forms.BooleanField(required=True, error_messages={"required": "Please confirm that you are not a robot."}, label="I'm not a robot")


class NebulaAuthenticationForm(HumanCheckMixin, AuthenticationForm):
    username = forms.EmailField(label="Email address", widget=forms.EmailInput(attrs={"autocomplete": "username", "autofocus": True}))

    def clean(self):
        email, password = self.cleaned_data.get("username"), self.cleaned_data.get("password")
        if email and password:
            self.user_cache = authenticate(self.request, username=email.strip().lower(), password=password)
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


class RegisterForm(HumanCheckMixin, forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    class Meta:
        model = Customer
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Customer.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

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
        customer.set_password(self.cleaned_data["password1"])
        if commit:
            customer.save()
        return customer


class AccountProfileForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ("first_name", "last_name", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Customer.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("An account with this email already exists.")
        return email


class AccountPasswordChangeForm(PasswordChangeForm):
    pass


class AccountPasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        for customer in Customer.objects.filter(email__iexact=email.strip().lower(), is_active=True):
            if customer.has_usable_password():
                yield customer
