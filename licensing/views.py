""""JSON API for the Nebula Vault desktop client's license checks."""

import base64
import json
import os
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .services import activate_license, deactivate_license, validate_license


RATE_LIMIT = 60
RATE_WINDOW_SECONDS = 60
MAX_BODY_BYTES = 16 * 1024
LEASE_SCHEMA = 1


def _b64url(data):
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _sign_offline_lease(license_obj, device_fingerprint):
    """Issue a short-lived, device-bound lease signed only by the server.

    NEBULA_LICENSE_SIGNING_PRIVATE_KEY must contain a base64url-encoded 32-byte
    Ed25519 private seed. Keep it in the deployment secret manager/environment;
    never put it in source control or the desktop package.
    """
    encoded_seed = os.environ.get("NEBULA_LICENSE_SIGNING_PRIVATE_KEY", "").strip()
    if not encoded_seed:
        # Fail closed: a valid online response may still work, but no offline
        # entitlement is minted without a production signing key.
        return None
    try:
        seed = base64.urlsafe_b64decode(encoded_seed + "=" * (-len(encoded_seed) % 4))
        if len(seed) != 32:
            raise ValueError("Expected 32-byte Ed25519 private seed")
        private_key = Ed25519PrivateKey.from_private_bytes(seed)
    except (ValueError, TypeError) as exc:
        raise RuntimeError("NEBULA_LICENSE_SIGNING_PRIVATE_KEY is invalid") from exc

    now = int(time.time())
    subscription = license_obj.subscription
    # The subscription end date is authoritative. A lease can never outlive it.
    entitlement_end = int(subscription.expires_at.timestamp())
    # The lease matches the full purchased subscription term. This improves
    # offline usability but means an offline device cannot learn about a revocation
    # until it next reaches the server.
    expires_at = entitlement_end
    if expires_at <= now:
        return None
    payload = {
        "schema": LEASE_SCHEMA,
        "license_id": str(license_obj.pk),
        "device_fingerprint": str(device_fingerprint),
        "issued_at": now,
        "expires_at": expires_at,
    }
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    signature = private_key.sign(payload_bytes)
    return _b64url(payload_bytes) + "." + _b64url(signature)


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


def _respond(result, device_fingerprint=""):
    data = {"ok": result.ok, "code": result.code, "message": result.message}
    if result.ok and result.license:
        license_obj = result.license
        subscription = license_obj.subscription
        customer = subscription.user
        full_name = " ".join(
            part.strip() for part in (customer.first_name, customer.last_name)
            if part and part.strip()
        )
        first_activation_at = (
            license_obj.activations.order_by("first_activated_at")
            .values_list("first_activated_at", flat=True)
            .first()
        )
        data.update({
            "license_id": str(license_obj.pk),
            "status": license_obj.status,
            "starts_at": subscription.starts_at.isoformat(),
            "expires_at": subscription.expires_at.isoformat(),
            "first_activated_at": first_activation_at.isoformat() if first_activation_at else None,
            "product": subscription.product.slug,
            "device_limit": license_obj.activation_limit,
            "active_devices": license_obj.active_activation_count,
            "buyer_name": full_name or customer.username or customer.email,
            "buyer_email": customer.email,
            "customer_id": str(customer.pk),
            "buyer_username": customer.username,
        })
        if device_fingerprint:
            data["signed_lease"] = _sign_offline_lease(license_obj, device_fingerprint)
    response = JsonResponse(data, status=200 if result.ok else 403)
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _error_response(code, message, status):
    response = JsonResponse({"ok": False, "code": code, "message": message}, status=status)
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _read_payload_or_error(request):
    if _rate_limited(request):
        return None, _error_response("rate_limited", "Too many requests.", 429)
    payload = _payload(request)
    if payload is None:
        return None, _error_response("invalid_request", "Send a valid JSON object under 16 KB.", 400)
    return payload, None


@csrf_exempt
@require_POST
def activate(request):
    payload, error = _read_payload_or_error(request)
    if error:
        return error
    fingerprint = payload.get("device_fingerprint", "")
    result = activate_license(
        payload.get("license_key", ""), fingerprint,
        payload.get("device_name", ""), payload.get("app_version", ""),
    )
    return _respond(result, fingerprint)


@csrf_exempt
@require_POST
def validate(request):
    payload, error = _read_payload_or_error(request)
    if error:
        return error
    fingerprint = payload.get("device_fingerprint", "")
    result = validate_license(
        payload.get("license_key", ""), fingerprint, payload.get("app_version", ""),
    )
    return _respond(result, fingerprint)


@csrf_exempt
@require_POST
def deactivate(request):
    payload, error = _read_payload_or_error(request)
    if error:
        return error
    result = deactivate_license(
        payload.get("license_key", ""), payload.get("device_fingerprint", ""),
    )
    return _respond(result)
