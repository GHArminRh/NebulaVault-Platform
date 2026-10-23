"""Authentication middleware for separate UUID-backed staff and customer models.

Django's stock middleware resolves a session user through the configured user
model before consulting the stored authentication backend. This project has two
user models, so resolve the user through the backend recorded in the session.
Both models now use UUID primary keys.
"""
from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY, load_backend
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.utils.crypto import constant_time_compare
from django.utils.functional import SimpleLazyObject


def get_session_user(request):
    """Resolve the active user through the backend recorded in the session."""
    user_id = request.session.get(SESSION_KEY)
    backend_path = request.session.get(BACKEND_SESSION_KEY)
    if user_id is None or backend_path not in settings.AUTHENTICATION_BACKENDS:
        return AnonymousUser()

    try:
        user = load_backend(backend_path).get_user(user_id)
    except (ValueError, TypeError, OverflowError):
        return AnonymousUser()

    if user is None or not getattr(user, "is_active", True):
        return AnonymousUser()

    session_hash = request.session.get(HASH_SESSION_KEY)
    if not session_hash:
        return AnonymousUser()

    try:
        if constant_time_compare(session_hash, user.get_session_auth_hash()):
            return user

        for secret in getattr(settings, "SECRET_KEY_FALLBACKS", []):
            if constant_time_compare(
                session_hash, user.get_session_auth_hash(secret=secret)
            ):
                request.session.cycle_key()
                request.session[HASH_SESSION_KEY] = user.get_session_auth_hash()
                return user
    except (AttributeError, TypeError):
        return AnonymousUser()

    request.session.flush()
    return AnonymousUser()


class UUIDCompatibleAuthenticationMiddleware(AuthenticationMiddleware):
    """Restore authentication using the backend associated with the session."""

    def process_request(self, request):
        if not hasattr(request, "session"):
            raise RuntimeError(
                "Authentication middleware requires session middleware to be installed. "
                "Edit MIDDLEWARE to insert "
                "'django.contrib.sessions.middleware.SessionMiddleware' before "
                "'staff_access.middleware.UUIDCompatibleAuthenticationMiddleware'."
            )
        request.user = SimpleLazyObject(lambda: get_session_user(request))
