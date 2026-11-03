"""Choose a default interface language from the visitor's IP, with a persistent manual override."""
from __future__ import annotations

import ipaddress
import json
import urllib.request

from django.core.exceptions import ValidationError
from django.utils.deprecation import MiddlewareMixin

LANGUAGE_COOKIE = "nv_language"
COOKIE_MAX_AGE = 60 * 60 * 24 * 180


def country_for_ip(ip: str) -> str:
    try:
        address = ipaddress.ip_address(ip)
        if not address.is_global:
            return ""
        request = urllib.request.Request(
            f"https://ipapi.co/{address.compressed}/json/",
            headers={"User-Agent": "NebulaVault/1.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=1.5) as response:
            data = json.loads(response.read(4096).decode("utf-8"))
        return str(data.get("country_code", "")).upper()
    except Exception:
        # Geo lookup is best-effort; language selection must never prevent the site from loading.
        return ""


class InterfaceLanguageMiddleware(MiddlewareMixin):
    def process_request(self, request):
        selected = request.COOKIES.get(LANGUAGE_COOKIE, "").lower()
        if selected in {"fa", "en"}:
            request.site_language = selected
            request.language_was_selected = True
            return None

        ip = request.META.get("REMOTE_ADDR", "")
        country = country_for_ip(ip)
        request.site_language = "fa" if country == "IR" else "en"
        request.language_was_selected = False
        request.detected_country = country
        return None

    def process_response(self, request, response):
        if not getattr(request, "language_was_selected", True):
            response.set_cookie(
                LANGUAGE_COOKIE,
                getattr(request, "site_language", "en"),
                max_age=COOKIE_MAX_AGE,
                samesite="Lax",
                secure=request.is_secure(),
                httponly=False,
            )
        return response


class SeparateStaffAndCustomerSessionsMiddleware(MiddlewareMixin):
    """Restrict staff identities to the admin interface."""

    def process_request(self, request):
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import AnonymousUser
        from django.shortcuts import redirect

        if request.path == "/admin" or request.path.startswith("/admin/"):
            return None
        user = getattr(request, "user", None)
        try:
            is_authenticated = bool(user and user.is_authenticated)
        except (ValidationError, ValueError, TypeError):
            request.session.flush()
            request.user = AnonymousUser()
            return None

        if not is_authenticated:
            return None
        if isinstance(user, get_user_model()):
            if request.path.rstrip("/") == "/accounts/logout":
                return redirect("portal:home")
            request.user = AnonymousUser()
        return None
