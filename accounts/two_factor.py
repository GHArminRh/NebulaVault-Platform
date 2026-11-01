import base64
import hashlib
import hmac
import secrets
from io import BytesIO

import pyotp
import qrcode
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.utils.crypto import salted_hmac
from django.utils import timezone


def new_totp_secret():
    return pyotp.random_base32()


def _fernet():
    key = base64.urlsafe_b64encode(hashlib.sha256((settings.SECRET_KEY + ':nebula-totp-v1').encode('utf-8')).digest())
    return Fernet(key)


def encrypt_totp_secret(secret):
    return _fernet().encrypt(secret.encode('ascii')).decode('ascii')


def decrypt_totp_secret(secret):
    if not secret:
        return ''
    try:
        return _fernet().decrypt(secret.encode('ascii')).decode('ascii')
    except (InvalidToken, UnicodeError, ValueError):
        return ''


def verify_totp(secret, token):
    token = (token or "").replace(" ", "").strip()
    return bool(secret and len(token) == 6 and token.isdigit() and pyotp.TOTP(secret).verify(token, valid_window=1))


def provisioning_uri(secret, username):
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name="Nebula Vault")


def qr_data_uri(uri):
    image = qrcode.make(uri)
    output = BytesIO()
    image.save(output, format="PNG")
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"



def generate_recovery_codes(count=10):
    """Return one-time recovery codes; callers must display them only once."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    codes = []
    for _ in range(count):
        raw = "".join(secrets.choice(alphabet) for _ in range(12))
        codes.append(f"{raw[:4]}-{raw[4:8]}-{raw[8:]}")
    return codes


def _recovery_code_digest(code):
    normalized = (code or "").replace("-", "").replace(" ", "").strip().upper()
    if len(normalized) != 12:
        return ""
    return salted_hmac("accounts.two_factor_recovery_code", normalized, algorithm="sha256").hexdigest()


def store_recovery_codes(user, codes=None):
    """Persist only hashes and return the plaintext codes for one-time display."""
    codes = codes or generate_recovery_codes()
    user.recovery_codes = [_recovery_code_digest(code) for code in codes]
    user.save(update_fields=["recovery_codes"])
    return codes


def consume_recovery_code(user, code):
    digest = _recovery_code_digest(code)
    if not digest:
        return False
    for index, saved_digest in enumerate(user.recovery_codes or []):
        if hmac.compare_digest(saved_digest, digest):
            remaining = list(user.recovery_codes)
            remaining.pop(index)
            user.recovery_codes = remaining
            user.save(update_fields=["recovery_codes"])
            return True
    return False


def verify_email_challenge(user, token, purpose="login"):
    """Verify and consume the latest short-lived email challenge."""
    from .models import TwoFactorEmailChallenge

    token = (token or "").strip().replace(" ", "")
    if len(token) != 6 or not token.isdigit():
        return False
    challenge = TwoFactorEmailChallenge.objects.filter(
        user_type=user._meta.label_lower,
        user_id=str(user.pk),
        purpose=purpose,
        consumed_at__isnull=True,
        expires_at__gt=timezone.now(),
        failed_attempts__lt=5,
    ).order_by("-created_at").first()
    if challenge is None:
        return False
    digest = salted_hmac("accounts.two_factor_email_code", token, algorithm="sha256").hexdigest()
    if hmac.compare_digest(challenge.code_hash, digest):
        challenge.consumed_at = timezone.now()
        challenge.save(update_fields=["consumed_at"])
        return True
    challenge.failed_attempts += 1
    challenge.save(update_fields=["failed_attempts"])
    return False



def send_email_code(request, user, purpose="login"):
    """Send a rate-limited, short-lived 2FA email challenge."""
    import hashlib
    import logging
    from datetime import timedelta

    from django.conf import settings
    from django.core.cache import cache
    from django.core.mail import send_mail
    from django.utils import timezone

    from .models import TwoFactorEmailChallenge

    logger = logging.getLogger(__name__)
    recipient = (getattr(user, "email", "") or "").strip()
    if not recipient:
        return False

    identity = f"{user._meta.label_lower}:{user.pk}:{purpose}"
    throttle_key = "two-factor-email:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()
    if not cache.add(throttle_key, 1, timeout=60):
        return False

    now = timezone.now()
    TwoFactorEmailChallenge.objects.filter(
        user_type=user._meta.label_lower,
        user_id=str(user.pk),
        purpose=purpose,
        consumed_at__isnull=True,
    ).update(consumed_at=now)

    code = f"{secrets.randbelow(1_000_000):06d}"
    digest = salted_hmac("accounts.two_factor_email_code", code, algorithm="sha256").hexdigest()
    challenge = TwoFactorEmailChallenge.objects.create(
        user_type=user._meta.label_lower,
        user_id=str(user.pk),
        recipient=recipient,
        purpose=purpose,
        code_hash=digest,
        expires_at=now + timedelta(minutes=10),
    )
    try:
        send_mail(
            subject="کد تأیید دومرحله‌ای نبیولا والت",
            message=(
                f"کد تأیید شما: {code}\n\n"
                "این کد تا ۱۰ دقیقه معتبر است و فقط یک بار قابل استفاده است. "
                "اگر شما درخواست نداده‌اید، این پیام را نادیده بگیرید."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Could not send two-factor email code to account %s", user.pk)
        challenge.consumed_at = timezone.now()
        challenge.save(update_fields=["consumed_at"])
        cache.delete(throttle_key)
        raise
    return True
