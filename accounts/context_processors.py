"""Template context for the Cloudflare Turnstile widget."""
from django.conf import settings


def turnstile(request):
    return {
        "TURNSTILE_ENABLED": getattr(settings, "TURNSTILE_ENABLED", True),
        "TURNSTILE_SITE_KEY": getattr(settings, "TURNSTILE_SITE_KEY", ""),
    }



def social_auth(request):
    """Expose enabled customer social sign-in providers to storefront templates."""
    return {
        "SOCIAL_AUTH_GOOGLE_ENABLED": getattr(settings, "SOCIAL_AUTH_GOOGLE_ENABLED", False),
        "SOCIAL_AUTH_APPLE_ENABLED": False,
    }
