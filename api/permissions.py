from rest_framework.permissions import BasePermission


class IsCustomer(BasePermission):
    """Only authenticated customer accounts may access customer resources."""

    message = "Customer account authentication is required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and hasattr(user, "email")
            and hasattr(user, "is_banned")
            and not user.is_banned
            and user.is_active
        )
