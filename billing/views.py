import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from .models import PaymentAttempt, PaymentOrder
from .services import create_payment_attempt, finalize_payment, PaymentAttemptCreationError, PaymentFinalizationError, PaymentReferenceConflict
from .zarinpal import ZarinpalError, request_payment, verify_payment
logger = logging.getLogger(__name__)

def _amount(order):
    if order.currency != "IRR":
        raise ZarinpalError("زرین‌پال فقط برای سفارش‌های با واحد پول IRR فعال است؛ واحد پول طرح را بررسی کنید.")
    amount = int(order.amount_minor_units)
    if amount < 1000:
        raise ZarinpalError("حداقل مبلغ قابل پرداخت ۱۰۰۰ ریال است.")
    return amount

@login_required
@require_POST
def start_zarinpal_payment(request, order_id):
    order = get_object_or_404(PaymentOrder.objects.select_related("plan", "plan__product"), pk=order_id, user=request.user)
    if order.status != PaymentOrder.Status.PENDING:
        messages.info(request, "این سفارش در انتظار پرداخت نیست.")
        return redirect("portal:orders")
    try:
        amount = _amount(order)
        attempt = create_payment_attempt(user=request.user, order_id=order.pk, provider="zarinpal", idempotency_key=order.order_number)
        if attempt.provider_reference:
            # A pending attempt can be retried by rebuilding the deterministic StartPay URL.
            from django.conf import settings
            base = "https://sandbox.zarinpal.com/pg/StartPay/" if settings.ZARINPAL_SANDBOX else "https://www.zarinpal.com/pg/StartPay/"
            return redirect(base + attempt.provider_reference)
        callback = request.build_absolute_uri(reverse("billing:zarinpal_callback")) + f"?attempt={attempt.pk}"
        authority, payment_url = request_payment(amount_rial=amount, description=f"Nebula Vault | {order.plan.product.name} | {order.order_number}", callback_url=callback, email=request.user.email or "")
        attempt.provider_reference = authority
        attempt.status = PaymentAttempt.Status.PENDING
        attempt.save(update_fields=["provider_reference", "status", "updated_at"])
        return redirect(payment_url)
    except (ZarinpalError, PaymentAttemptCreationError, ValueError) as exc:
        logger.warning("Zarinpal request failed for order %s: %s", order.pk, exc)
        messages.error(request, str(exc))
        return redirect("portal:orders")

@require_GET
def zarinpal_callback(request):
    attempt_id = request.GET.get("attempt", "")
    authority = (request.GET.get("Authority") or "").strip()
    status = (request.GET.get("Status") or "").strip().upper()
    attempt = PaymentAttempt.objects.select_related("order", "order__plan", "order__plan__product").filter(pk=attempt_id, provider="zarinpal").first()
    if attempt is None:
        messages.error(request, "تلاش پرداخت پیدا نشد؛ در صورت کسر وجه با پشتیبانی تماس بگیرید.")
        return redirect("portal:orders")
    if attempt.status == PaymentAttempt.Status.SUCCEEDED and attempt.order.status == PaymentOrder.Status.PAID:
        messages.success(request, "این پرداخت قبلاً تأیید شده است.")
        return redirect("portal:orders")
    if not authority or status != "OK":
        attempt.status = PaymentAttempt.Status.CANCELED
        attempt.save(update_fields=["status", "updated_at"])
        messages.warning(request, "پرداخت لغو شد یا از سوی درگاه موفق اعلام نشد.")
        return redirect("portal:orders")
    try:
        if attempt.provider_reference != authority:
            raise PaymentReferenceConflict("شناسه درگاه با تلاش پرداخت ثبت‌شده مطابقت ندارد.")
        verified, reference, detail = verify_payment(amount_rial=_amount(attempt.order), authority=authority)
        if not verified:
            messages.error(request, f"زرین‌پال پرداخت را تأیید نکرد: {detail}")
            return redirect("portal:orders")
        # Clear temporary Authority before storing the verified RefID.\n        attempt.provider_reference = None\n        attempt.save(update_fields=["provider_reference", "updated_at"])\n        finalized = finalize_payment(attempt_id=attempt.pk, provider_reference=reference, confirmed_amount_minor_units=attempt.order.amount_minor_units, confirmed_currency=attempt.order.currency)
        key = getattr(finalized, "issued_license_key", None)
        if key:
            stored = request.session.get("nebula_new_license_keys", {})
            if not isinstance(stored, dict):
                stored = {}
            stored[str(attempt.order.order_number)] = key
            request.session["nebula_new_license_keys"] = stored
        messages.success(request, "پرداخت با موفقیت تأیید شد و سفارش تکمیل شد.")
    except (ZarinpalError, PaymentFinalizationError, PaymentReferenceConflict) as exc:
        logger.exception("Zarinpal callback failed for attempt %s", attempt.pk)
        messages.error(request, f"تأیید پرداخت کامل نشد: {exc}")
    return redirect("portal:orders")
