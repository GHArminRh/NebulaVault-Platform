"""ZarinPal SDK adapter for the Nebula Vault billing workflow.

All payment confirmation is server-to-server. Never trust callback query values
as proof of payment; the provider verification response is required.
"""
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


class ZarinPalError(Exception):
    """A safe-to-display payment gateway error."""


def _as_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict") and callable(value.dict):
        try:
            return value.dict()
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        return {k: v for k, v in vars(value).items() if not k.startswith("_")}
    return {}


def _pick(data: dict, *keys):
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    for container_key in ("data", "result", "payment", "authority", "transaction"):
        nested = data.get(container_key)
        if isinstance(nested, dict):
            found = _pick(nested, *keys)
            if found not in (None, ""):
                return found
    return None


def _client():
    merchant_id = getattr(settings, "ZARINPAL_MERCHANT_ID", "").strip()
    access_token = getattr(settings, "ZARINPAL_ACCESS_TOKEN", "").strip()
    if not merchant_id and not access_token:
        raise ZarinPalError("درگاه زرین‌پال هنوز در تنظیمات سرور پیکربندی نشده است.")
    try:
        from zarinpal import ZarinPal
        from zarinpal_utils.Config import Config
    except ImportError as exc:
        logger.exception("ZarinPal SDK import failed")
        raise ZarinPalError("کتابخانهٔ زرین‌پال نصب نیست؛ وابستگی‌های سرور را نصب کنید.") from exc

    kwargs = {"sandbox": bool(getattr(settings, "ZARINPAL_SANDBOX", False))}
    if merchant_id:
        kwargs["merchant_id"] = merchant_id
    if access_token:
        kwargs["access_token"] = access_token
    try:
        config = Config(**kwargs)
        return ZarinPal(config)
    except Exception as exc:
        logger.exception("ZarinPal SDK initialization failed")
        raise ZarinPalError("تنظیمات اتصال به زرین‌پال معتبر نیست.") from exc


def amount_to_rial(amount_minor_units: int, currency: str) -> int:
    """Convert the platform's integer price snapshot to the rial amount ZarinPal expects."""
    currency = (currency or "").upper()
    if currency == "IRR":
        amount = amount_minor_units
    elif currency == "IRT":
        amount = amount_minor_units * 10
    else:
        raise ZarinPalError(
            "زرین‌پال فقط برای سفارش‌های ریالی (IRR) یا تومانی (IRT) فعال است."
        )
    if amount < 1000:
        raise ZarinPalError("مبلغ سفارش برای پرداخت با زرین‌پال کمتر از حد مجاز است.")
    return amount


def create_gateway_payment(*, order, attempt, callback_url: str) -> tuple[str, str]:
    """Return (authority, redirect_url) after creating a provider-side payment."""
    amount = amount_to_rial(order.amount_minor_units, order.currency)
    description = f"Nebula Vault order {order.order_number}"
    payload = {
        "amount": amount,
        "description": description[:500],
        "callback_url": callback_url,
        "metadata": {
            "email": getattr(order.user, "email", "") or "",
            "mobile": "",
        },
    }
    try:
        response = _client().payment_gateway.create(payload)
        data = _as_dict(response)
        authority = _pick(data, "authority", "Authority", "authority_code")
        redirect_url = _pick(data, "url", "payment_url", "paymentUrl", "redirect_url", "checkout_url")
        if not authority or not redirect_url:
            logger.error("Unexpected ZarinPal create response keys: %s", sorted(data.keys()))
            raise ZarinPalError("پاسخ درگاه برای ایجاد پرداخت معتبر نبود.")
        authority = str(authority).strip()
        redirect_url = str(redirect_url).strip()
        if not authority or not redirect_url.startswith("https://"):
            raise ZarinPalError("نشانی انتقال به درگاه معتبر نیست.")
        return authority, redirect_url
    except ZarinPalError:
        raise
    except Exception as exc:
        logger.exception("ZarinPal payment creation failed")
        raise ZarinPalError("ارتباط با زرین‌پال برقرار نشد؛ کمی بعد دوباره تلاش کنید.") from exc


def verify_gateway_payment(*, authority: str, amount_minor_units: int, currency: str) -> dict:
    """Verify a callback with ZarinPal and return its normalized response."""
    amount = amount_to_rial(amount_minor_units, currency)
    client = _client()
    payload = {"authority": authority, "amount": amount}
    gateway = client.payment_gateway
    method = getattr(gateway, "verify", None) or getattr(gateway, "verify_payment", None)
    if method is None:
        raise ZarinPalError(
            "نسخهٔ نصب‌شدهٔ SDK زرین‌پال متد تأیید پرداخت را ارائه نمی‌کند."
        )
    try:
        response = method(payload)
        data = _as_dict(response)
        status = _pick(data, "code", "status", "Status", "code_status")
        ref_id = _pick(data, "ref_id", "refId", "RefID", "transaction_id", "id")
        try:
            status_number = int(status)
        except (TypeError, ValueError):
            status_number = None
        # The v4 gateway convention returns 100 for a successful verification.
        # Also accept an explicit boolean success only if the SDK exposes it.
        success = status_number in (100, 101) or data.get("success") is True or data.get("ok") is True
        if not success:
            logger.warning("ZarinPal verification rejected (status=%r)", status)
            raise ZarinPalError("زرین‌پال پرداخت را تأیید نکرد.")
        return {"success": True, "authority": authority, "ref_id": str(ref_id or authority), "raw_status": status}
    except ZarinPalError:
        raise
    except Exception as exc:
        logger.exception("ZarinPal payment verification failed")
        raise ZarinPalError("تأیید پرداخت از زرین‌پال ناموفق بود؛ وضعیت سفارش تغییر نکرد.") from exc


def payment_redirect_url(authority: str) -> str:
    """Rebuild the provider redirect URL for an already-created attempt."""
    from urllib.parse import quote
    if not authority or len(authority) > 255:
        raise ZarinPalError("شناسهٔ پرداخت معتبر نیست.")
    base = "https://sandbox.zarinpal.com/pg/StartPay/" if getattr(settings, "ZARINPAL_SANDBOX", False) else "https://www.zarinpal.com/pg/StartPay/"
    return base + quote(authority, safe="")
