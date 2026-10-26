"""License issuance and validation primitives used by admin and the client API."""

import base64
import hashlib
import secrets
import string
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import License, LicenseActivation


_KEY_ALPHABET = string.ascii_uppercase + string.digits
_ENCRYPTED_KEY_MARKER = "[[NEBULA_LICENSE_KEY:"
_ENCRYPTED_KEY_END = "]]"


def _key_digest(key):
    if not isinstance(key, str):
        return ""
    return hashlib.sha256(key.strip().upper().encode("utf-8")).hexdigest()


def _fingerprint_digest(fingerprint):
    if not isinstance(fingerprint, str):
        return ""
    return hashlib.sha256(fingerprint.strip().encode("utf-8")).hexdigest()


def _fernet():
    """Derive a stable encryption key from Django's secret; never store plaintext."""
    material = hashlib.sha256(
        (settings.SECRET_KEY + "|nebula-license-key-v1").encode("utf-8")
    ).digest()
    return Fernet(base64.urlsafe_b64encode(material))


def _save_encrypted_key(record, key):
    encrypted = _fernet().encrypt(key.encode("utf-8")).decode("ascii")
    notes = record.notes or ""
    start = notes.find(_ENCRYPTED_KEY_MARKER)
    if start >= 0:
        end = notes.find(_ENCRYPTED_KEY_END, start)
        if end >= 0:
            notes = (notes[:start] + notes[end + len(_ENCRYPTED_KEY_END):]).strip()
    marker = f"{_ENCRYPTED_KEY_MARKER}{encrypted}{_ENCRYPTED_KEY_END}"
    record.notes = f"{notes}\n{marker}".strip() if notes else marker
    record.save(update_fields=["notes", "updated_at"])


def get_stored_license_key(record):
    """Decrypt a key stored on newly issued licenses; legacy hashes are not reversible."""
    notes = record.notes or ""
    start = notes.find(_ENCRYPTED_KEY_MARKER)
    if start < 0:
        return ""
    value_start = start + len(_ENCRYPTED_KEY_MARKER)
    end = notes.find(_ENCRYPTED_KEY_END, value_start)
    if end < 0:
        return ""
    try:
        return _fernet().decrypt(notes[value_start:end].encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeError, ValueError):
        return ""


def generate_license_key():
    """Generate a high-entropy key; callers must never log it."""
    raw = "".join(secrets.choice(_KEY_ALPHABET) for _ in range(32))
    return "NVL-" + "-".join(raw[i:i + 4] for i in range(0, len(raw), 4))


def issue_license(subscription, notes=""):
    """Issue a license, storing only a digest plus an encrypted recoverable copy."""
    key = generate_license_key()
    record = License.objects.create(
        subscription=subscription,
        key_prefix=key[:8],
        key_digest=_key_digest(key),
        notes=notes,
    )
    _save_encrypted_key(record, key)
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


def _inactive_license_result(license_record):
    """Return a stable machine-readable reason for an inactive license."""
    if license_record.status == License.Status.SUSPENDED:
        return LicenseResult(False, "license_suspended", "Your license has been suspended by the server.")
    return LicenseResult(False, "license_inactive", "The license is not currently active.")


def activate_license(key, fingerprint, device_label="", app_version=""):
    """Activate a device only if it has never been deactivated for this license."""
    if not _valid_fingerprint(fingerprint):
        return LicenseResult(False, "invalid_device", "A valid device fingerprint is required.")
    license_record = _find_license(key)
    if license_record is None:
        return LicenseResult(False, "invalid_license", "The license key is invalid.")
    if not license_record.is_entitled:
        return _inactive_license_result(license_record)

    fingerprint_hash = _fingerprint_digest(fingerprint)
    label = device_label[:120] if isinstance(device_label, str) else ""
    version = app_version[:40] if isinstance(app_version, str) else ""

    with transaction.atomic():
        locked = License.objects.select_for_update(of=("self",)).get(pk=license_record.pk)
        # Serialize the first-activation date calculation against paid renewals.
        from subscriptions.models import Subscription

        locked_subscription = (
            Subscription.objects.select_for_update(of=("self",))
            .select_related("user", "product", "plan")
            .get(pk=locked.subscription_id)
        )
        locked.subscription = locked_subscription

        if not locked.is_entitled:
            return _inactive_license_result(locked)

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

        # Deactivation is a persistent block for this device/license pair. Never
        # flip the same activation back to active just because the key is re-entered.
        # An administrator can explicitly restore access in the admin interface.
        if activation is not None:
            return LicenseResult(
                False,
                "device_deactivated",
                "This device has been deactivated for this license and cannot reactivate by re-entering the key.",
                activation,
                locked,
            )

        had_any_activation = locked.activations.exists()
        if (
            not had_any_activation
            and locked.subscription.kind == locked.subscription.Kind.PAID
            and locked.subscription.plan_id is None
        ):
            return LicenseResult(
                False,
                "license_inactive",
                "The paid license has no subscription plan.",
            )

        active_count = locked.activations.filter(is_active=True).count()
        if active_count >= locked.activation_limit:
            return LicenseResult(False, "device_limit_reached", "The license has reached its device activation limit.")

        try:
            with transaction.atomic():
                activation = LicenseActivation.objects.create(
                    license=locked,
                    fingerprint_digest=fingerprint_hash,
                    device_label=label,
                    app_version=version,
                    first_activated_at=now,
                    last_seen_at=now,
                )
        except IntegrityError:
            return LicenseResult(False, "activation_conflict", "The activation could not be completed; please retry.")

        # The first successful desktop activation starts the purchased term.
        # Include each paid period already purchased, including verified renewals.
        if not had_any_activation:
            subscription = locked.subscription
            if subscription.kind == subscription.Kind.PAID:
                plan = subscription.plan
                from subscriptions.services import _add_plan_duration

                expiry = now
                period_count = 1 + subscription.renewals.count()
                for _ in range(period_count):
                    expiry = _add_plan_duration(expiry, plan)

                subscription.starts_at = now
                subscription.expires_at = expiry
                subscription.save(update_fields=["starts_at", "expires_at", "updated_at"])

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
        return _inactive_license_result(license_record)

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
        return LicenseResult(False, "device_not_activated", "The device is not activated for the license.")
    activation.is_active = False
    activation.deactivated_at = timezone.now()
    activation.save(update_fields=["is_active", "deactivated_at"])
    return LicenseResult(True, "deactivated", "The device has been deactivated.", activation, license_record)
