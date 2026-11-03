from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from allauth.socialaccount.forms import SignupForm as SocialSignupForm


def store_customer_consent(user, cleaned_data):
    if not cleaned_data.get("accept_terms"):
        raise ValidationError("پذیرش قوانین و مقررات برای ساخت حساب الزامی است.")
    user.terms_accepted_at = timezone.now()
    user.terms_version = getattr(settings, "TERMS_VERSION", "2026-11-04")
    user.newsletter_opt_in = bool(cleaned_data.get("newsletter_opt_in"))
    user.newsletter_opt_in_at = timezone.now() if user.newsletter_opt_in else None
    user.save(update_fields=[
        "terms_accepted_at",
        "terms_version",
        "newsletter_opt_in",
        "newsletter_opt_in_at",
    ])


class ConsentFieldsMixin:
    accept_terms = forms.BooleanField(
        required=True,
        label="قوانین و مقررات نبیولا والت را می‌پذیرم.",
    )
    newsletter_opt_in = forms.BooleanField(
        required=False,
        initial=False,
        label="مایلم آخرین اخبار و اطلاعیه‌ها را دریافت کنم.",
    )


class CustomerSignupExtraForm(ConsentFieldsMixin, forms.Form):
    def signup(self, request, user):
        store_customer_consent(user, self.cleaned_data)


class CustomerSocialSignupForm(ConsentFieldsMixin, SocialSignupForm):
    pass
