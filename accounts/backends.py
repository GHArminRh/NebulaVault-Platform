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

        if customer.check_password(password) and customer.is_active and not customer.is_banned:
            return customer
        return None

    def get_user(self, user_id):
        # Customer primary keys are UUIDs. A malformed or legacy session ID must
        # be treated as an anonymous session, not allowed to raise a 500 error.
        try:
            return Customer.objects.get(pk=user_id, is_active=True, is_banned=False)
        except (Customer.DoesNotExist, ValidationError, ValueError, TypeError):
            return None



class WagtailGroupPermissionsBackend(BaseBackend):
    """Apply permissions granted through the separate Wagtail auth.Group relation.

    The project deliberately uses UUID-backed staff.Group records for its
    existing Django admin. Wagtail's page/document permission models use
    django.contrib.auth.Group, so these memberships are stored separately.
    """

    def get_group_permissions(self, user_obj, obj=None):
        if obj is not None or not getattr(user_obj, "is_active", False):
            return set()
        if not hasattr(user_obj, "wagtail_groups"):
            return set()

        from django.contrib.auth.models import Permission

        permissions = Permission.objects.filter(
            group__in=user_obj.wagtail_groups.all()
        ).values_list("content_type__app_label", "codename")
        return {f"{app_label}.{codename}" for app_label, codename in permissions}

    def has_perm(self, user_obj, perm, obj=None):
        if not getattr(user_obj, "is_active", False):
            return False
        if getattr(user_obj, "is_superuser", False):
            return True
        return perm in self.get_group_permissions(user_obj, obj)
