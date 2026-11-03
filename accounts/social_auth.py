"""OpenID Connect clients for customer-only Google and Apple sign-in."""
from datetime import datetime, timedelta, timezone

import jwt
from authlib.integrations.django_client import OAuth
from django.conf import settings


class SocialAuthNotConfigured(Exception):
    pass


def _apple_client_secret():
    now = datetime.now(timezone.utc)
    claims = {
        "iss": settings.APPLE_OAUTH_TEAM_ID,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=180)).timestamp()),
        "aud": "https://appleid.apple.com",
        "sub": settings.APPLE_OAUTH_CLIENT_ID,
    }
    return jwt.encode(
        claims,
        settings.APPLE_OAUTH_PRIVATE_KEY,
        algorithm="ES256",
        headers={"kid": settings.APPLE_OAUTH_KEY_ID},
    )


def get_oauth_client(provider):
    """Return a fresh provider client so Apple's short-lived client secret is renewed."""
    oauth = OAuth()
    if provider == "google" and settings.SOCIAL_AUTH_GOOGLE_ENABLED:
        oauth.register(
            name="google",
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
    elif provider == "apple" and settings.SOCIAL_AUTH_APPLE_ENABLED:
        oauth.register(
            name="apple",
            client_id=settings.APPLE_OAUTH_CLIENT_ID,
            client_secret=_apple_client_secret(),
            server_metadata_url="https://appleid.apple.com/.well-known/openid-configuration",
            client_kwargs={"scope": "name email"},
            token_endpoint_auth_method="client_secret_post",
        )
    else:
        raise SocialAuthNotConfigured(provider)
    return oauth.create_client(provider)
