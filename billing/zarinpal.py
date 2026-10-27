"""Minimal Zarinpal v4 client; sandbox is the default."""
import json
import logging
import re
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


class ZarinpalError(Exception):
    """A safe, user-facing payment gateway error."""


def _config():
    merchant_id = getattr(settings, "ZARINPAL_MERCHANT_ID", "").strip()
    if not merchant_id:
        raise ZarinpalError("شناسه پذیرنده زرین‌پال تنظیم نشده است.")
    sandbox = getattr(settings, "ZARINPAL_SANDBOX", True)
    base = "https://sandbox.zarinpal.com" if sandbox else "https://payment.zarinpal.com"
    return merchant_id, base, sandbox


def amount_in_rials(amount_minor_units, currency):
    """Convert the order's whole-unit IRR/IRT amount to the Rial API amount."""
    currency = (currency or "").upper()
    amount = int(amount_minor_units)
    if amount <= 0:
        raise ZarinpalError("مبلغ سفارش معتبر نیست.")
    # The catalog stores amounts in hundredths of the displayed currency
    # (e.g. USD 1999 means USD 19.99). Zarinpal accepts whole Rials.
    if currency == "IRR":
        if amount % 100:
            raise ZarinpalError("مبلغ ریالی باید مضرب ۱۰۰ واحد ذخیره‌شده باشد.")
        return amount // 100
    if currency == "IRT":
        if amount % 10:
            raise ZarinpalError("مبلغ تومانی برای تبدیل به ریال دقیق نیست.")
        return amount // 10
    raise ZarinpalError("زرین‌پال فقط برای سفارش‌های ریالی یا تومانی فعال است.")


def _safe_gateway_error_details(raw_body):
    """Return only short, redacted gateway error codes/messages for diagnostics."""
    try:
        body = json.loads(raw_body.decode("utf-8", errors="replace"))
    except (TypeError, ValueError):
        return "non_json_response"

    errors = body.get("errors") if isinstance(body, dict) else None
    if not errors and isinstance(body, dict):
        errors = body.get("data", {}).get("errors") if isinstance(body.get("data"), dict) else None
    if isinstance(errors, dict):
        items = [errors]
    elif isinstance(errors, list):
        items = [item for item in errors if isinstance(item, dict)][:5]
    else:
        return "gateway_error_details_unavailable"

    details = []
    for item in items:
        code = item.get("code")
        message = item.get("message") or item.get("messages")
        if isinstance(message, list):
            message = "; ".join(str(part) for part in message[:3])
        if message is not None:
            message = str(message)
            # Avoid leaking customer details or request credentials if echoed by the gateway.
            message = re.sub(r"https?://\S+", "[url]", message, flags=re.IGNORECASE)
            message = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email]", message)
            message = re.sub(r"\b[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\b", "[uuid]", message, flags=re.IGNORECASE)
            message = re.sub(r"\b\d{7,}\b", "[number]", message)
            message = message[:300]
        if code is not None or message:
            details.append({"code": code, "message": message})
    return json.dumps(details, ensure_ascii=False, separators=(",", ":"))[:1200] if details else "gateway_error_details_unavailable"


def _post_json(url, payload):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            details = _safe_gateway_error_details(exc.read(8192))
        except (OSError, ValueError):
            details = "response_body_unavailable"
        logger.warning(
            "Zarinpal HTTP error: host=%s status=%s gateway_details=%s",
            request.host, exc.code, details,
        )
        raise ZarinpalError(
            f"پاسخ سرور زرین‌پال خطای HTTP {exc.code} بود. گزارش برنامه را برای جزئیات بررسی کنید."
        ) from exc
    except urllib.error.URLError as exc:
        logger.warning(
            "Zarinpal connection error: host=%s reason=%r",
            request.host, getattr(exc, "reason", exc),
        )
        raise ZarinpalError(
            "اتصال سرور به زرین‌پال برقرار نشد؛ گزارش برنامه را برای علت شبکه، DNS یا TLS بررسی کنید."
        ) from exc
    except (TimeoutError, OSError) as exc:
        logger.warning(
            "Zarinpal transport error: host=%s error=%s",
            request.host, type(exc).__name__,
        )
        raise ZarinpalError(
            "اتصال به زرین‌پال زمان‌بر شد یا از سمت شبکه قطع شد؛ گزارش برنامه را بررسی کنید."
        ) from exc
    except (ValueError, UnicodeDecodeError) as exc:
        logger.warning("Zarinpal returned invalid JSON: host=%s", request.host)
        raise ZarinpalError("پاسخ زرین‌پال قابل‌خواندن نبود؛ گزارش برنامه را بررسی کنید.") from exc
    if not isinstance(result, dict):
        raise ZarinpalError("پاسخ دریافتی از زرین‌پال معتبر نیست.")
    return result


def request_payment(*, amount, description, callback_url, email=None, mobile=None):
    merchant_id, base, sandbox = _config()
    metadata = {}
    if email:
        metadata["email"] = email[:100]
    if mobile:
        metadata["mobile"] = mobile[:20]
    payload = {
        "merchant_id": merchant_id,
        "amount": int(amount),
        "description": str(description)[:500],
        "callback_url": callback_url,
    }
    if metadata:
        payload["metadata"] = metadata
    result = _post_json(f"{base}/pg/v4/payment/request.json", payload)
    data = result.get("data") or {}
    if data.get("code") != 100 or not data.get("authority"):
        errors = result.get("errors") or {}
        raise ZarinpalError("درخواست پرداخت توسط زرین‌پال پذیرفته نشد. کد: " + str(data.get("code", errors.get("code", "نامشخص"))))
    authority = str(data["authority"])
    start_base = "https://sandbox.zarinpal.com/pg/StartPay/" if sandbox else "https://www.zarinpal.com/pg/StartPay/"
    return authority, start_base + authority


def verify_payment(*, authority, amount):
    merchant_id, base, _ = _config()
    result = _post_json(
        f"{base}/pg/v4/payment/verify.json",
        {"merchant_id": merchant_id, "amount": int(amount), "authority": authority},
    )
    data = result.get("data") or {}
    code = data.get("code")
    # 101 means this authority has already been verified by the gateway.
    if code not in (100, 101):
        raise ZarinpalError("تأیید پرداخت از طرف زرین‌پال انجام نشد. کد: " + str(code or "نامشخص"))
    return {"code": code, "ref_id": str(data.get("ref_id", "")), "data": data}
