"""License issuance and validation primitives used by admin and the client API."""

import hashlib
import secrets
import string
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import License, LicenseActivation


_KEY_ALPHABET = string.ascii_uppercase + string.digits


def _key_digest(key):
    if not isinstance(key, str):
        return ""
    return hashlib.sha256(key.strip().upper().encode("utf-8")).hexdigest()


def _fingerprint_digest(fingerprint):
    if not isinstance(fingerprint, str):
        return ""
    return hashlib.sha256(fingerprint.strip().encode("utf-8")).hexdigest()


def generate_license_key():
    """Generate a high-entropy key; callers must show it once and never log it."""
    raw = "".join(secrets.choice(_KEY_ALPHABET) for _ in range(32))
    return "NVL-" + "-".join(raw[i:i + 4] for i in range(0, len(raw), 4))


def issue_license(subscription, notes=""):
    """Issue a license and return (license_record, plaintext_key)."""
    key = generate_license_key()
    record = License.objects.create(
        subscription=subscription,
        key_prefix=key[:8],
        key_digest=_key_digest(key),
        notes=notes,
    )
    return record, key


@dataclass(frozen=True)
class LicenseResult:
    ok: bool
    code: str
    message: str
    activation: LicenseActivation | None = None
    license: License | None = None


def _find_license(key):
    if not isinstance(key, str) or not key or len(key) > 80:
        return None
    try:
        return License.objects.select_related(
            "subscription", "subscription__user", "subscription__product", "subscription__plan"
        ).get(key_digest=_key_digest(key))
    except License.DoesNotExist:
        return None


def _valid_fingerprint(fingerprint):
    return isinstance(fingerprint, str) and 8 <= len(fingerprint.strip()) <= 512


def activate_license(key, fingerprint, device_label="", app_version=""):
    """Activate a device, enforcing current entitlement and the plan's device limit."""
    if not _valid_fingerprint(fingerprint):
        return LicenseResult(False, "invalid_device", "A valid device fingerprint is required.")
    license_record = _find_license(key)
    if license_record is None:
        return LicenseResult(False, "invalid_license", "The license key is invalid.")
    if not license_record.is_entitled:
        return LicenseResult(False, "license_inactive", "The license is not currently active.")

    fingerprint_hash = _fingerprint_digest(fingerprint)
    label = device_label[:120] if isinstance(device_label, str) else ""
    version = app_version[:40] if isinstance(app_version, str) else ""

    with transaction.atomic():
        # Lock only the License row. Locking the select_related joins as well can
        # make PostgreSQL reject the query when subscription__plan is nullable.
        locked = License.objects.select_for_update(of=("self",)).select_related(
            "subscription", "subscription__user", "subscription__product", "subscription__plan"
        ).get(pk=license_record.pk)
        if not locked.is_entitled:
            return LicenseResult(False, "license_inactive", "The license is not currently active.")

        activation = LicenseActivation.objects.filter(
            license=locked, fingerprint_digest=fingerprint_hash
        ).first()
        now = timezone.now()
        if activation and activation.is_active:
            activation.device_label = label or activation.device_label
            activation.app_version = version or activation.app_version
            activation.last_seen_at = now
            activation.save(update_fields=["device_label", "app_version", "last_seen_at"])
            locked.last_validated_at = now
            locked.save(update_fields=["last_validated_at", "updated_at"])
            return LicenseResult(True, "activated", "This device is activated.", activation, locked)

        active_count = locked.activations.filter(is_active=True).count()
        if active_count >= locked.activation_limit:
            return LicenseResult(False, "device_limit_reached", "The license has reached its device activation limit.")

        if activation:
            activation.is_active = True
            activation.device_label = label
            activation.app_version = version
            activation.last_seen_at = now
            activation.deactivated_at = None
            activation.save(update_fields=[
                "is_active", "device_label", "app_version", "last_seen_at", "deactivated_at"
            ])
        else:
            try:
                # A nested atomic block ensures a uniqueness race does not poison the outer transaction.
                with transaction.atomic():
                    activation = LicenseActivation.objects.create(
                        license=locked,
                        fingerprint_digest=fingerprint_hash,
                        device_label=label,
                        app_version=version,
                    )
            except IntegrityError:
                return LicenseResult(False, "activation_conflict", "The activation could not be completed; please retry.")

        locked.last_validated_at = now
        locked.save(update_fields=["last_validated_at", "updated_at"])
        return LicenseResult(True, "activated", "This device is activated.", activation, locked)


def validate_license(key, fingerprint, app_version=""):
    """Validate an existing device activation without silently activating new devices."""
    if not _valid_fingerprint(fingerprint):
        return LicenseResult(False, "invalid_device", "A valid device fingerprint is required.")
    license_record = _find_license(key)
    if license_record is None:
        return LicenseResult(False, "invalid_license", "The license key is invalid.")
    if not license_record.is_entitled:
        return LicenseResult(False, "license_inactive", "The license is not currently active.")

    activation = LicenseActivation.objects.filter(
        license=license_record,
        fingerprint_digest=_fingerprint_digest(fingerprint),
        is_active=True,
    ).first()
    if activation is None:
        return LicenseResult(False, "device_not_activated", "This device is not activated for the license.")

    now = timezone.now()
    activation.last_seen_at = now
    if isinstance(app_version, str) and app_version:
        activation.app_version = app_version[:40]
    activation.save(update_fields=["last_seen_at", "app_version"])
    license_record.last_validated_at = now
    license_record.save(update_fields=["last_validated_at", "updated_at"])
    return LicenseResult(True, "valid", "The license is valid for this device.", activation, license_record)


def deactivate_license(key, fingerprint):
    """Deactivate a matching device even if the license was suspended or revoked."""
    if not _valid_fingerprint(fingerprint):
        return LicenseResult(False, "invalid_device", "A valid device fingerprint is required.")
    license_record = _find_license(key)
    if license_record is None:
        return LicenseResult(False, "invalid_license", "The license key is invalid.")
    activation = LicenseActivation.objects.filter(
        license=license_record,
        fingerprint_digest=_fingerprint_digest(fingerprint),
        is_active=True,
    ).first()
    if activation is None:
        return LicenseResult(False, "device_not_activated", "This device is not activated for the license.")
    activation.is_active = False
    activation.deactivated_at = timezone.now()
    activation.save(update_fields=["is_active", "deactivated_at"])
    return LicenseResult(True, "deactivated", "This device has been deactivated.", activation, license_record)
