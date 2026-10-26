"""Thin, timeout-bounded adapter around the official ZarinPal Python SDK.

The gateway never decides whether an order is paid. Only a successful server-side
verification is returned to the billing view, which then calls finalize_payment.
"""
from functools import partial
from urllib.parse import urlsplit

from django.conf import settings


class ZarinPalGatewayError(Exception):
    """A safe-to-display payment gateway error."""


def _client():
    if not getattr(settings, "ZARINPAL_MERCHANT_ID", ""):
        raise ZarinPalGatewayError("درگاه زرین‌پال هنوز در تنظیمات سرور پیکربندی نشده است.")

    try:
        from zarinpal import ZarinPal
        from zarinpal_utils.Config import Config
    except ImportError as exc:
        raise ZarinPalGatewayError(
            "کتابخانه رسمی زرین‌پال نصب نیست؛ وابستگی‌های سرور را به‌روزرسانی کنید."
        ) from exc

    config = Config(
        sandbox=settings.ZARINPAL_SANDBOX,
        merchant_id=settings.ZARINPAL_MERCHANT_ID,
        access_token=getattr(settings, "ZARINPAL_ACCESS_TOKEN", "") or None,
    )
    client = ZarinPal(config)

    # SDK public API currently has no request-timeout argument; attach one to
    # its requests-based transport so a provider outage cannot hang a worker.
    original_request = client.http_client.request
    client.http_client.request = partial(
        original_request,
        timeout=getattr(settings, "ZARINPAL_HTTP_TIMEOUT", 15),
    )
    return client


def _data(response):
    """Return the provider's data object without assuming a single envelope."""
    if not isinstance(response, dict):
        raise ZarinPalGatewayError("پاسخ نامعتبر از درگاه پرداخت دریافت شد.")
    payload = response.get("data", response)
    if not isinstance(payload, dict):
        raise ZarinPalGatewayError("ساختار پاسخ درگاه پرداخت معتبر نیست.")
    return payload


def _provider_code(payload):
    try:
        return int(payload.get("code"))
    except (TypeError, ValueError):
        return None


def validate_callback_url(callback_url):
    """Reject malformed callback URLs and insecure production callbacks."""
    parsed = urlsplit(callback_url or "")
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ZarinPalGatewayError(
            "نشانی بازگشت پرداخت معتبر نیست؛ ZARINPAL_PUBLIC_BASE_URL را بررسی کنید."
        )
    if not settings.DEBUG and parsed.scheme != "https":
        raise ZarinPalGatewayError("نشانی بازگشت در محیط عملیاتی باید HTTPS باشد.")
    return callback_url


def request_payment(*, amount_irr, callback_url, description, email=""):
    """Create a ZarinPal payment request; return (authority, payment_url)."""
    if isinstance(amount_irr, bool) or not isinstance(amount_irr, int) or amount_irr < 1000:
        raise ZarinPalGatewayError("مبلغ پرداخت باید دست‌کم ۱۰۰۰ ریال باشد.")

    callback_url = validate_callback_url(callback_url)
    client = _client()
    request_data = {
        "amount": amount_irr,
        "callback_url": callback_url,
        "description": str(description)[:500],
    }
    if email:
        request_data["metadata"] = {"email": str(email)[:254]}

    try:
        response = client.payments.create(request_data)
        payload = _data(response)
        authority = payload.get("authority")
        if _provider_code(payload) != 100 or not isinstance(authority, str) or not authority.strip():
            raise ZarinPalGatewayError("زرین‌پال درخواست پرداخت را نپذیرفت.")
        authority = authority.strip()
        payment_url = client.payments.generate_payment_url(authority)
        parsed_url = urlsplit(payment_url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise ZarinPalGatewayError("نشانی انتقال به درگاه معتبر نیست.")
        return authority, payment_url
    except ZarinPalGatewayError:
        raise
    except Exception as exc:
        raise ZarinPalGatewayError(
            "ارتباط با درگاه زرین‌پال برقرار نشد. لطفاً بعداً دوباره تلاش کنید."
        ) from exc


def verify_payment(*, amount_irr, authority):
    """Verify a payment against ZarinPal's server; return stable provider reference."""
    if isinstance(amount_irr, bool) or not isinstance(amount_irr, int) or amount_irr < 1000:
        raise ZarinPalGatewayError("مبلغ پرداخت برای تأیید معتبر نیست.")
    if not isinstance(authority, str) or not authority.strip() or len(authority) > 64:
        raise ZarinPalGatewayError("شناسه پرداخت زرین‌پال معتبر نیست.")

    try:
        client = _client()
        response = client.verifications.verify({
            "amount": amount_irr,
            "authority": authority.strip(),
        })
        payload = _data(response)
        # 100 = verified; 101 = already verified. Accept 101 for callback retries.
        if _provider_code(payload) not in {100, 101}:
            raise ZarinPalGatewayError(
                "زرین‌پال پرداخت را تأیید نکرد. تا تأیید قطعی، سفارش پرداخت‌شده محسوب نمی‌شود."
            )
        return authority.strip()
    except ZarinPalGatewayError:
        raise
    except Exception as exc:
        raise ZarinPalGatewayError(
            "تأیید پرداخت از زرین‌پال ناموفق بود؛ سفارش در انتظار بررسی باقی می‌ماند."
        ) from exc
