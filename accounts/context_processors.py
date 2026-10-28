"""Template context for the public-facing Cloudflare Turnstile widget."""
from django.conf import settings


def turnstile(request):
    return {
        "TURNSTILE_SITE_KEY": getattr(settings, "TURNSTILE_SITE_KEY", ""),
    }
