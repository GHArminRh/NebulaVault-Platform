import hashlib
import hmac
from datetime import timedelta

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import CustomerAPIToken


class CustomerBearerAuthentication(BaseAuthentication):
    """Authenticate customer API calls using a hashed, expiring Bearer token."""

    keyword = "Bearer"

    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        if not header:
            return None

        parts = header.split()
        if len(parts) != 2 or parts[0].casefold() != self.keyword.casefold():
            return None

        raw_token = parts[1]
        if len(raw_token) < 32 or len(raw_token) > 256:
            raise AuthenticationFailed("Invalid API token.")

        digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        prefix = raw_token[:12]
        token = (
            CustomerAPIToken.objects.select_related("customer")
            .filter(token_prefix=prefix)
            .first()
        )
        if token is None or not hmac.compare_digest(token.token_digest, digest):
            raise AuthenticationFailed("Invalid API token.")

        now = timezone.now()
        if token.revoked_at is not None:
            raise AuthenticationFailed("This API token has been revoked.")
        if token.expires_at <= now:
            raise AuthenticationFailed("This API token has expired.")
        if not token.customer.is_active or token.customer.is_banned:
            raise AuthenticationFailed("This account cannot access the API.")

        # Keep the last-used timestamp useful without writing on every request.
        if token.last_used_at is None or now - token.last_used_at >= timedelta(minutes=5):
            CustomerAPIToken.objects.filter(pk=token.pk).update(last_used_at=now)
        return token.customer, token

    def authenticate_header(self, request):
        return self.keyword


class CustomerSessionAuthentication(SessionAuthentication):
    """Use the project's existing dual-user-model session middleware."""
