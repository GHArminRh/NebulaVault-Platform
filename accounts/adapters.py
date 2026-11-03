from django.core.exceptions import ValidationError
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .social_forms import store_customer_consent


class CustomerSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        if form is None or not getattr(form, "cleaned_data", {}).get("accept_terms"):
            raise ValidationError("پذیرش قوانین و مقررات برای ساخت حساب الزامی است.")
        user = super().save_user(request, sociallogin, form=form)
        store_customer_consent(user, form.cleaned_data)
        return user
