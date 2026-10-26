"""Small, defensive adapter for Zarinpal's v4 payment API.

Amounts are sent in Rial. This project stores order amounts in the currency's
minor unit, so Zarinpal checkout deliberately accepts IRR orders only.
"""
from __future__ import annotations

import requests
from django.conf import settings


class ZarinpalError(Exception):
    """Raised when Zarinpal rejects a request or cannot be reached."""


def _config():
    merchant_id = str(getattr(settings, "ZARINPAL_MERCHANT_ID", "") or "").strip()
    if not merchant_id:
        raise ZarinpalError("درگاه زرین‌پال هنوز پیکربندی نشده است.")
    sandbox = bool(getattr(settings, "ZARINPAL_SANDBOX", True))
    api_base = (
        "https://sandbox.zarinpal.com/pg/v4/payment"
        if sandbox else "https://api.zarinpal.com/pg/v4/payment"
    )
    startpay_base = (
        "https://sandbox.zarinpal.com/pg/StartPay/"
        if sandbox else "https://www.zarinpal.com/pg/StartPay/"
    )
    return merchant_id, api_base, startpay_base


def _post(url: str, payload: dict) -> dict:
    try:
        response = requests.post(url, json=payload, timeout=(5, 20))
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise ZarinpalError("ارتباط با درگاه زرین‌پال برقرار نشد؛ کمی بعد دوباره تلاش کنید.") from exc
    if not isinstance(data, dict):
        raise ZarinpalError("پاسخ نامعتبر از درگاه زرین‌پال دریافت شد.")
    return data


def request_payment(*, amount_rial: int, description: str, callback_url: str, email: str = "") -> tuple[str, str]:
    if isinstance(amount_rial, bool) or not isinstance(amount_rial, int) or amount_rial < 1000:
        raise ZarinpalError("مبلغ پرداخت باید حداقل ۱۰۰۰ ریال باشد.")
    merchant_id, api_base, startpay_base = _config()
    payload = {
        "merchant_id": merchant_id,
        "amount": amount_rial,
        "description": description[:500],
        "callback_url": callback_url,
        "metadata": {"email": email} if email else {},
    }
    data = _post(f"{api_base}/request.json", payload)
    errors = data.get("errors") or {}
    result = data.get("data") or {}
    code = result.get("code")
    if code not in (100, 101) or not result.get("authority"):
        message = errors.get("message") if isinstance(errors, dict) else ""
        raise ZarinpalError(str(message or f"درخواست پرداخت از سوی زرین‌پال رد شد (کد {code})."))
    authority = str(result["authority"])
    return authority, f"{startpay_base}{authority}"


def verify_payment(*, amount_rial: int, authority: str) -> tuple[bool, str, str]:
    """Return (verified, reference, provider message)."""
    merchant_id, api_base, _ = _config()
    data = _post(f"{api_base}/verify.json", {
        "merchant_id": merchant_id,
        "amount": amount_rial,
        "authority": authority,
    })
    result = data.get("data") or {}
    errors = data.get("errors") or {}
    code = result.get("code")
    reference = result.get("ref_id") or result.get("refid") or ""
    if code in (100, 101) and reference:
        return True, str(reference), "پرداخت تأیید شد."
    message = errors.get("message") if isinstance(errors, dict) else ""
    return False, "", str(message or f"تأیید پرداخت ناموفق بود (کد {code}).")
