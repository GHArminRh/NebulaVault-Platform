"""Account-scoped protection for customer API token issuance."""

import hashlib
import hmac
import secrets
from datetime import timedelta
from math import ceil

from django.conf import settings
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from .models import TokenLoginFailure

FAILURE_WINDOW = timedelta(minutes=15)
LOCKOUT_THRESHOLD = 5
BASE_LOCKOUT_SECONDS = 30
MAX_LOCKOUT_SECONDS = 15 * 60
STALE_RECORD_AGE = timedelta(days=1)


def _email_digest(email):
    normalized = (email or "").strip().casefold()
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        normalized.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def get_token_login_lockout_seconds(email, now=None):
    """Return remaining account lockout seconds without exposing account state."""
    now = now or timezone.now()
    record = TokenLoginFailure.objects.filter(pk=_email_digest(email)).only("locked_until").first()
    if record is None or record.locked_until is None or record.locked_until <= now:
        return 0
    return max(1, ceil((record.locked_until - now).total_seconds()))


def record_token_login_failure(email, now=None):
    """Atomically record a failed attempt and apply progressive account lockout."""
    now = now or timezone.now()
    digest = _email_digest(email)

    with transaction.atomic():
        if connection.vendor == "postgresql":
            # Serialize first-time inserts as well as updates without relying
            # on a racy cache increment or emitting expected unique-key errors.
            lock_id = int.from_bytes(bytes.fromhex(digest[:16]), "big", signed=True)
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock_id])

        try:
            record = TokenLoginFailure.objects.select_for_update().get(pk=digest)
        except TokenLoginFailure.DoesNotExist:
            try:
                # The savepoint lets a concurrent first insert win cleanly.
                with transaction.atomic():
                    record = TokenLoginFailure.objects.create(
                        email_digest=digest,
                        failed_attempts=0,
                        window_started_at=now,
                    )
            except IntegrityError:
                record = TokenLoginFailure.objects.select_for_update().get(pk=digest)

        if now - record.window_started_at >= FAILURE_WINDOW:
            record.failed_attempts = 0
            record.window_started_at = now
            record.locked_until = None

        record.failed_attempts += 1
        if record.failed_attempts >= LOCKOUT_THRESHOLD:
            exponent = record.failed_attempts - LOCKOUT_THRESHOLD
            lockout_seconds = min(
                BASE_LOCKOUT_SECONDS * (2 ** exponent),
                MAX_LOCKOUT_SECONDS,
            )
            record.locked_until = now + timedelta(seconds=lockout_seconds)

        record.save(
            update_fields=(
                "failed_attempts",
                "window_started_at",
                "locked_until",
                "updated_at",
            )
        )

    # Bound storage for arbitrary, attacker-submitted email addresses. Digests
    # older than one day are no longer useful for enforcing this policy.
    if secrets.randbelow(128) == 0:
        TokenLoginFailure.objects.filter(updated_at__lt=now - STALE_RECORD_AGE).delete()

    return record.failed_attempts, get_token_login_lockout_seconds(email, now=now)


def clear_token_login_failures(email):
    """Reset the account counter after a fully successful password + 2FA login."""
    TokenLoginFailure.objects.filter(pk=_email_digest(email)).delete()
