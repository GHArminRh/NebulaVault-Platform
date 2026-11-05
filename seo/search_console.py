"""Google Search Console OAuth and Search Analytics API helpers."""
from __future__ import annotations

import base64
import hashlib
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API_ROOT = "https://www.googleapis.com/webmasters/v3"
SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"


class SearchConsoleError(Exception):
    """Raised when Google OAuth or Search Console API calls fail."""


def _fernet():
    key = base64.urlsafe_b64encode(
        hashlib.sha256((settings.SECRET_KEY + ":nebula-gsc-refresh-v1").encode("utf-8")).digest()
    )
    return Fernet(key)


def encrypt_refresh_token(token: str) -> str:
    return _fernet().encrypt(token.encode("utf-8")).decode("ascii")


def decrypt_refresh_token(token: str) -> str:
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeError, ValueError):
        raise SearchConsoleError("Stored Google refresh token could not be decrypted.") from None


def _client_config():
    client_id = getattr(settings, "GOOGLE_SEARCH_CONSOLE_CLIENT_ID", "")
    client_secret = getattr(settings, "GOOGLE_SEARCH_CONSOLE_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise SearchConsoleError("Google OAuth Client ID and Client Secret are not configured.")
    return client_id, client_secret


def authorization_url(*, redirect_uri: str, state: str) -> str:
    client_id, _ = _client_config()
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return AUTH_URL + "?" + urlencode(params)


def _post_form(url: str, values: dict) -> dict:
    body = urlencode(values).encode("utf-8")
    request = Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read(1_000_000).decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read(4000).decode("utf-8", errors="replace")
        raise SearchConsoleError(f"Google returned HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise SearchConsoleError(f"Could not contact Google: {exc}") from exc


def exchange_code(*, code: str, redirect_uri: str) -> dict:
    client_id, client_secret = _client_config()
    result = _post_form(TOKEN_URL, {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    })
    if not result.get("access_token"):
        raise SearchConsoleError("Google OAuth did not return an access token.")
    return result


def refresh_access_token(refresh_token: str) -> str:
    client_id, client_secret = _client_config()
    result = _post_form(TOKEN_URL, {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
    })
    access_token = result.get("access_token")
    if not access_token:
        raise SearchConsoleError("Google did not return a refreshed access token.")
    return access_token


def query_search_analytics(*, access_token: str, site_url: str, start_date: str,
                           end_date: str, dimensions: list[str]) -> list[dict]:
    endpoint = f"{API_ROOT}/sites/{quote(site_url, safe='')}/searchAnalytics/query"
    rows = []
    start_row = 0
    while True:
        payload = json.dumps({
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": dimensions,
            "type": "web",
            "dataState": "final",
            "rowLimit": 25000,
            "startRow": start_row,
        }).encode("utf-8")
        request = Request(endpoint, data=payload, headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        try:
            with urlopen(request, timeout=30) as response:
                data = json.loads(response.read(5_000_000).decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read(4000).decode("utf-8", errors="replace")
            raise SearchConsoleError(f"Search Console API returned HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            raise SearchConsoleError(f"Search Console API request failed: {exc}") from exc
        batch = data.get("rows", [])
        rows.extend(batch)
        if len(batch) < 25000:
            break
        start_row += len(batch)
        if start_row >= 100000:
            break
    return rows
