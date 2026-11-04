"""Staff-only Google Search Console OAuth connection views."""
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core import signing
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from .models import SearchConsoleConnection
from .search_console import (
    SearchConsoleError,
    authorization_url,
    encrypt_refresh_token,
    exchange_code,
)


STATE_SESSION_KEY = "seo_gsc_oauth_state"
STATE_SALT = "nebula-seo-search-console-oauth"


def _redirect_uri(request):
    configured = getattr(settings, "GOOGLE_SEARCH_CONSOLE_REDIRECT_URI", "")
    return configured or request.build_absolute_uri(
        reverse("seo-search-console-callback")
    )


def _valid_property(value):
    value = (value or "").strip()
    if value.startswith("sc-domain:"):
        domain = value.removeprefix("sc-domain:").strip().lower()
        return bool(domain and "/" not in domain and " " not in domain and "." in domain)
    parts = urlsplit(value)
    return (
        parts.scheme == "https"
        and bool(parts.hostname)
        and not parts.username
        and not parts.password
        and not parts.query
        and not parts.fragment
        and parts.path in {"", "/"}
    )


@staff_member_required
@require_POST
def search_console_connect(request):
    site_url = (request.POST.get("site_url") or "").strip()
    if not _valid_property(site_url):
        messages.error(request, "Enter a valid HTTPS URL-prefix property or sc-domain:example.com property.")
        return redirect("seo-dashboard")
    if site_url.startswith("https://") and not site_url.endswith("/"):
        site_url += "/"
    if not settings.GOOGLE_SEARCH_CONSOLE_CLIENT_ID or not settings.GOOGLE_SEARCH_CONSOLE_CLIENT_SECRET:
        messages.error(request, "Google OAuth Client ID and Client Secret must first be configured in the server environment.")
        return redirect("seo-dashboard")
    state = signing.dumps(
        {"site_url": site_url, "user_id": str(request.user.pk)},
        salt=STATE_SALT,
    )
    request.session[STATE_SESSION_KEY] = state
    try:
        url = authorization_url(redirect_uri=_redirect_uri(request), state=state)
    except SearchConsoleError as exc:
        messages.error(request, str(exc))
        return redirect("seo-dashboard")
    return redirect(url)


@staff_member_required
@require_GET
def search_console_callback(request):
    expected_state = request.session.pop(STATE_SESSION_KEY, "")
    supplied_state = request.GET.get("state", "")
    if not expected_state or not supplied_state or not secrets_compare(expected_state, supplied_state):
        messages.error(request, "Google OAuth state validation failed. Please try connecting again.")
        return redirect("seo-dashboard")
    try:
        state_data = signing.loads(supplied_state, salt=STATE_SALT, max_age=600)
    except signing.BadSignature:
        messages.error(request, "Google OAuth request expired or was invalid.")
        return redirect("seo-dashboard")
    if state_data.get("user_id") != str(request.user.pk):
        messages.error(request, "The Google connection was started by a different admin session.")
        return redirect("seo-dashboard")
    if request.GET.get("error"):
        messages.error(request, "Google authorization was not completed.")
        return redirect("seo-dashboard")
    code = request.GET.get("code", "")
    if not code:
        messages.error(request, "Google did not return an authorization code.")
        return redirect("seo-dashboard")

    site_url = state_data["site_url"]
    try:
        token_data = exchange_code(code=code, redirect_uri=_redirect_uri(request))
        connection = SearchConsoleConnection.objects.filter(site_url=site_url).first()
        refresh_token = token_data.get("refresh_token")
        if not refresh_token and connection:
            encrypted_refresh_token = connection.refresh_token_encrypted
        elif refresh_token:
            encrypted_refresh_token = encrypt_refresh_token(refresh_token)
        else:
            raise SearchConsoleError(
                "Google did not issue a refresh token. Revoke the previous app grant in Google Account permissions and reconnect."
            )
        SearchConsoleConnection.objects.update_or_create(
            site_url=site_url,
            defaults={
                "refresh_token_encrypted": encrypted_refresh_token,
                "granted_scope": token_data.get("scope", ""),
                "is_active": True,
                "last_sync_error": "",
            },
        )
    except SearchConsoleError as exc:
        messages.error(request, str(exc))
        return redirect("seo-dashboard")

    messages.success(request, f"Google Search Console connected for {site_url}.")
    return redirect("seo-dashboard")


def secrets_compare(left, right):
    import hmac
    return hmac.compare_digest(left, right)
