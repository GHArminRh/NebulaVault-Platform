"""JSON API for the Nebula Vault desktop client's license checks."""

import json

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .services import activate_license, deactivate_license, validate_license


RATE_LIMIT = 60
RATE_WINDOW_SECONDS = 60
MAX_BODY_BYTES = 16 * 1024


def _rate_limited(request):
    address = request.META.get("REMOTE_ADDR", "unknown")
    key = f"licensing:api:{address}"
    try:
        if cache.add(key, 1, timeout=RATE_WINDOW_SECONDS):
            return False
        return cache.incr(key) > RATE_LIMIT
    except (ValueError, NotImplementedError):
        return False


def _payload(request):
    if len(request.body) > MAX_BODY_BYTES:
        return None
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _respond(result):
    data = {"ok": result.ok, "code": result.code, "message": result.message}
    if result.ok and result.license:
        data.update({
            "license_id": str(result.license.pk),
            "status": result.license.status,
            "expires_at": result.license.subscription.expires_at.isoformat(),
            "product": result.license.subscription.product.slug,
            "device_limit": result.license.activation_limit,
            "active_devices": result.license.active_activation_count,
        })
    response = JsonResponse(data, status=200 if result.ok else 403)
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _read_payload_or_error(request):
    if _rate_limited(request):
        return None, JsonResponse({"ok": False, "code": "rate_limited", "message": "Too many requests."}, status=429)
    payload = _payload(request)
    if payload is None:
        return None, JsonResponse({"ok": False, "code": "invalid_request", "message": "Send a valid JSON object under 16 KB."}, status=400)
    return payload, None


@csrf_exempt
@require_POST
def activate(request):
    payload, error = _read_payload_or_error(request)
    if error:
        return error
    result = activate_license(
        payload.get("license_key", ""),
        payload.get("device_fingerprint", ""),
        payload.get("device_name", ""),
        payload.get("app_version", ""),
    )
    return _respond(result)


@csrf_exempt
@require_POST
def validate(request):
    payload, error = _read_payload_or_error(request)
    if error:
        return error
    result = validate_license(
        payload.get("license_key", ""),
        payload.get("device_fingerprint", ""),
        payload.get("app_version", ""),
    )
    return _respond(result)


@csrf_exempt
@require_POST
def deactivate(request):
    payload, error = _read_payload_or_error(request)
    if error:
        return error
    result = deactivate_license(
        payload.get("license_key", ""),
        payload.get("device_fingerprint", ""),
    )
    return _respond(result)
