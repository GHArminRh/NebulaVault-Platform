"""Authentication middleware that supports UUID customer IDs alongside Django staff IDs.

Django's stock auth middleware converts the session user ID using
get_user_model().pk.to_python() before it calls the configured backend. Since
this project intentionally keeps Django's built-in User for staff and uses a
separate UUID-primary-key Customer model, that conversion rejects customer
UUIDs before CustomerAuthenticationBackend.get_user() can run.
"""
from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY, load_backend
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.utils.crypto import constant_time_compare
from django.utils.functional import SimpleLazyObject


def get_session_user(request):
    """Resolve the user using the session's backend without assuming an integer PK."""
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

        # Support Django's configured SECRET_KEY rotation behavior.
        for secret in getattr(settings, "SECRET_KEY_FALLBACKS", []):
            if constant_time_compare(
                session_hash, user.get_session_auth_hash(secret=secret)
            ):
                request.session.cycle_key()
                request.session[HASH_SESSION_KEY] = user.get_session_auth_hash()
                return user
    except (AttributeError, TypeError):
        return AnonymousUser()

    # A changed password or invalid auth hash invalidates the session.
    request.session.flush()
    return AnonymousUser()


class UUIDCompatibleAuthenticationMiddleware(AuthenticationMiddleware):
    """Keep standard Django session auth while allowing UUID customer primary keys."""

    def process_request(self, request):
        if not hasattr(request, "session"):
            raise RuntimeError(
                "Authentication middleware requires session middleware to be installed. "
                "Edit MIDDLEWARE to insert "
                "'django.contrib.sessions.middleware.SessionMiddleware' before "
                "'accounts.middleware.UUIDCompatibleAuthenticationMiddleware'."
            )
        # Django's admin login uses the built-in integer-PK User model. If a
        # customer UUID session is already present, auth_login() tries to coerce
        # that old session ID to an integer before replacing it with the staff ID.
        # End the customer session before processing the admin login form.
        if (
            request.path.rstrip("/") == "/admin/login"
            and request.session.get(BACKEND_SESSION_KEY)
            == "accounts.backends.CustomerAuthenticationBackend"
        ):
            request.session.flush()

        request.user = SimpleLazyObject(lambda: get_session_user(request))
