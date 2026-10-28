"""Fail-closed Cloudflare Turnstile Siteverify client."""
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def verify_turnstile(token, *, secret_key, verify_url):
    """Return True only when Cloudflare confirms the submitted token."""
    if not token or not secret_key:
        return False

    payload = {"secret": secret_key, "response": token}
    request = Request(
        verify_url,
        data=urlencode(payload).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
        return result.get("success") is True
    except Exception:
        # Fail closed on timeouts, network errors, and malformed provider responses.
        return False
