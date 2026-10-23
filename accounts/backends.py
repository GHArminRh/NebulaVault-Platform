from django.contrib.auth.backends import BaseBackend
from django.core.exceptions import ValidationError
from .models import Customer


class CustomerAuthenticationBackend(BaseBackend):
    """Authenticate site customers independently of Django staff users."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = (kwargs.get("email") or username or "").strip().lower()
        if not email or password is None:
            return None

        try:
            customer = Customer.objects.get(email__iexact=email)
        except Customer.DoesNotExist:
            # Keep the response timing less dependent on whether an account exists.
            from django.contrib.auth.hashers import make_password
            make_password(password)
            return None

        if customer.check_password(password) and customer.is_active:
            return customer
        return None

    def get_user(self, user_id):
        # Customer primary keys are UUIDs. A malformed or legacy session ID must
        # be treated as an anonymous session, not allowed to raise a 500 error.
        try:
            return Customer.objects.get(pk=user_id, is_active=True)
        except (Customer.DoesNotExist, ValidationError, ValueError, TypeError):
            return None
