import logging
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from .models import PaymentAttempt, PaymentOrder
from .services import PaymentAttemptCreationError, PaymentFinalizationError, PaymentReferenceConflict, create_payment_attempt, finalize_payment
from .zarinpal import ZarinPalError, create_gateway_payment, payment_redirect_url, verify_gateway_payment

logger = logging.getLogger(__name__)


@login_required
@require_POST
def zarinpal_start(request, order_id):
    order = get_object_or_404(PaymentOrder, pk=order_id, user=request.user)
    if order.status != PaymentOrder.Status.PENDING:
        messages.info(request, "این سفارش در انتظار پرداخت نیست.")
        return redirect("portal:orders")
    if not getattr(settings, "ZARINPAL_MERCHANT_ID", "").strip() and not getattr(settings, "ZARINPAL_ACCESS_TOKEN", "").strip():
        messages.error(request, "درگاه زرین‌پال هنوز توسط مدیر سایت پیکربندی نشده است.")
        return redirect("portal:orders")
    try:
        attempt = create_payment_attempt(user=request.user, order_id=order.pk, provider="zarinpal", idempotency_key=request.POST.get("idempotency_key") or uuid.uuid4())
        if attempt.status == PaymentAttempt.Status.SUCCEEDED:
            messages.success(request, "این سفارش قبلاً پرداخت شده است.")
            return redirect("portal:orders")
        if attempt.provider_reference:
            return redirect(payment_redirect_url(attempt.provider_reference))
        callback_url = request.build_absolute_uri(reverse("billing:zarinpal_callback"))
        authority, redirect_url = create_gateway_payment(order=order, attempt=attempt, callback_url=callback_url)
        attempt.provider_reference = authority
        attempt.status = PaymentAttempt.Status.PENDING
        attempt.save(update_fields=["provider_reference", "status", "updated_at"])
        return redirect(redirect_url)
    except (PaymentAttemptCreationError, ZarinPalError) as exc:
        messages.error(request, str(exc))
        return redirect("portal:orders")


@require_GET
def zarinpal_callback(request):
    authority = (request.GET.get("Authority") or "").strip()
    status = (request.GET.get("Status") or "").strip().lower()
    if not authority or len(authority) > 255:
        messages.error(request, "پاسخ بازگشت از درگاه معتبر نیست.")
        return redirect("portal:home")
    attempt = PaymentAttempt.objects.select_related("order", "order__user", "order__plan").filter(provider="zarinpal", provider_reference=authority).first()
    if attempt is None:
        messages.error(request, "تلاش پرداخت متناظر با این پاسخ پیدا نشد.")
        return redirect("portal:home")
    if attempt.status == PaymentAttempt.Status.SUCCEEDED and attempt.order.status == PaymentOrder.Status.PAID:
        messages.success(request, "پرداخت این سفارش قبلاً تأیید شده است.")
        return redirect("portal:orders")
    if status != "ok":
        attempt.status = PaymentAttempt.Status.CANCELED
        attempt.save(update_fields=["status", "updated_at"])
        messages.warning(request, "پرداخت انجام نشد یا توسط کاربر لغو شد.")
        return redirect("portal:orders")
    try:
        verify_gateway_payment(authority=authority, amount_minor_units=attempt.order.amount_minor_units, currency=attempt.order.currency)
        finalize_payment(attempt_id=attempt.pk, provider_reference=authority, confirmed_amount_minor_units=attempt.order.amount_minor_units, confirmed_currency=attempt.order.currency)
    except (ZarinPalError, PaymentFinalizationError, PaymentReferenceConflict) as exc:
        logger.warning("ZarinPal callback could not finalize order %s: %s", attempt.order_id, exc)
        messages.error(request, "تأیید نهایی پرداخت انجام نشد. اگر مبلغ کسر شده، با پشتیبانی تماس بگیرید.")
        return redirect("portal:orders")
    messages.success(request, "پرداخت با موفقیت تأیید و سفارش شما فعال شد.")
    return redirect("portal:orders")
