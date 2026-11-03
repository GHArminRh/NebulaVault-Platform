"""Template context for the Cloudflare Turnstile widget."""
from django.conf import settings


def turnstile(request):
    return {
        "TURNSTILE_ENABLED": getattr(settings, "TURNSTILE_ENABLED", True),
        "TURNSTILE_SITE_KEY": getattr(settings, "TURNSTILE_SITE_KEY", ""),
    }
