import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from catalog.models import Plan
from .models import PaymentAttempt, PaymentOrder
from .services import (
    OrderCreationError, PaymentAttemptCreationError, PaymentFinalizationError,
    create_payment_attempt, create_payment_order, create_cart_payment_order, finalize_payment,
)
from .zarinpal import ZarinpalError, amount_in_rials, request_payment, verify_payment


@login_required
@require_POST
def start_zarinpal_payment(request, plan_id):
    """Create an order/attempt server-side, then redirect to Zarinpal."""
    if not getattr(settings, "ZARINPAL_ENABLED", True):
        messages.error(request, "درگاه زرین‌پال در حال حاضر غیرفعال است.")
        return redirect("portal:pricing")
    plan = get_object_or_404(Plan.objects.select_related("product"), pk=plan_id,
                             is_active=True, product__is_active=True)
    try:
        order = PaymentOrder.objects.filter(
            user=request.user, plan=plan, status=PaymentOrder.Status.PENDING,
            subscription__isnull=True,
        ).order_by("-created_at").first()
        if order is None:
            order = create_payment_order(
                user=request.user, plan_id=plan.pk, idempotency_key=uuid.uuid4(),
            )
        amount = amount_in_rials(order.amount_minor_units, order.currency)
        attempt = create_payment_attempt(
            user=request.user, order_id=order.pk, provider="zarinpal",
            idempotency_key=uuid.uuid4(),
        )
        if attempt.provider_reference:
            base = ("https://sandbox.zarinpal.com/pg/StartPay/" if
                    getattr(settings, "ZARINPAL_SANDBOX", True) else
                    "https://www.zarinpal.com/pg/StartPay/")
            return redirect(base + attempt.provider_reference)
        callback_url = request.build_absolute_uri(reverse("billing:zarinpal_callback"))
        authority, payment_url = request_payment(
            amount=amount,
            description=f"Nebula Vault order {order.order_number}",
            callback_url=callback_url,
            email=getattr(request.user, "email", None),
        )
        attempt.provider_reference = authority
        attempt.status = PaymentAttempt.Status.PENDING
        attempt.save(update_fields=["provider_reference", "status", "updated_at"])
        return redirect(payment_url)
    except (OrderCreationError, PaymentAttemptCreationError, ZarinpalError, ValueError) as exc:
        messages.error(request, f"شروع پرداخت ممکن نشد: {exc}")
        return redirect("portal:pricing")


@login_required
@require_POST
def start_zarinpal_cart_payment(request):
    """Pay an unchanged cart snapshot in one Zarinpal transaction."""
    if not getattr(settings, "ZARINPAL_ENABLED", True):
        messages.error(request, "درگاه زرین‌پال در حال حاضر غیرفعال است.")
        return redirect("portal:cart")
    plan_ids = request.session.get("nebula_cart", [])
    if not isinstance(plan_ids, list) or not plan_ids:
        messages.error(request, "سبد خرید خالی است.")
        return redirect("portal:cart")
    try:
        order = create_cart_payment_order(user=request.user, plan_ids=plan_ids)
        amount = amount_in_rials(order.amount_minor_units, order.currency)
        attempt = create_payment_attempt(
            user=request.user, order_id=order.pk, provider="zarinpal",
            idempotency_key=uuid.uuid4(),
        )
        if attempt.provider_reference:
            base = ("https://sandbox.zarinpal.com/pg/StartPay/" if
                    getattr(settings, "ZARINPAL_SANDBOX", True) else
                    "https://www.zarinpal.com/pg/StartPay/")
            return redirect(base + attempt.provider_reference)
        callback_url = request.build_absolute_uri(reverse("billing:zarinpal_callback"))
        authority, payment_url = request_payment(
            amount=amount, description=f"Nebula Vault cart order {order.order_number}",
            callback_url=callback_url, email=getattr(request.user, "email", None),
        )
        attempt.provider_reference = authority
        attempt.status = PaymentAttempt.Status.PENDING
        attempt.save(update_fields=["provider_reference", "status", "updated_at"])
        return redirect(payment_url)
    except (OrderCreationError, PaymentAttemptCreationError, ZarinpalError, ValueError) as exc:
        messages.error(request, f"شروع پرداخت سبد خرید ممکن نشد: {exc}")
        return redirect("portal:cart")


@require_GET
def zarinpal_callback(request):
    """Verify the callback server-to-server before granting access."""
    authority = (request.GET.get("Authority") or "").strip()
    status = (request.GET.get("Status") or "").strip().upper()
    if not authority or len(authority) > 255:
        return render(request, "billing/payment_result.html", {
            "success": False, "message": "اطلاعات بازگشت از درگاه معتبر نیست.",
        }, status=400)
    attempt = PaymentAttempt.objects.select_related("order", "order__plan").filter(
        provider="zarinpal", provider_reference=authority,
    ).first()
    if attempt is None:
        return render(request, "billing/payment_result.html", {
            "success": False, "message": "تراکنش مربوط به این درخواست پیدا نشد.",
        }, status=404)
    if status != "OK":
        if attempt.status in (PaymentAttempt.Status.CREATED, PaymentAttempt.Status.PENDING):
            attempt.status = PaymentAttempt.Status.CANCELED
            attempt.save(update_fields=["status", "updated_at"])
        return render(request, "billing/payment_result.html", {
            "success": False, "message": "پرداخت توسط کاربر لغو شد یا تکمیل نشد.",
            "order": attempt.order,
        })
    try:
        amount = amount_in_rials(attempt.amount_minor_units, attempt.currency)
        verified = verify_payment(authority=authority, amount=amount)
        with transaction.atomic():
            finalized = finalize_payment(
                attempt_id=attempt.pk,
                provider_reference=authority,
                confirmed_amount_minor_units=attempt.amount_minor_units,
                confirmed_currency=attempt.currency,
            )
        cart_items = list(attempt.order.items.all())
        if cart_items:
            expected_ids = [str(item.plan_id) for item in cart_items]
            current_ids = request.session.get("nebula_cart", [])
            if isinstance(current_ids, list) and list(dict.fromkeys(map(str, current_ids))) == expected_ids:
                request.session["nebula_cart"] = []
        return render(request, "billing/payment_result.html", {
            "success": True,
            "message": "پرداخت با موفقیت تأیید شد و دسترسی همه طرح‌های سفارش فعال شد.",
            "order": attempt.order,
            "reference": verified.get("ref_id") or authority,
            "sandbox": getattr(settings, "ZARINPAL_SANDBOX", True),
            "license_key": getattr(finalized, "issued_license_key", None),
            "license_keys": getattr(finalized, "issued_license_keys", []),
        })
    except (ZarinpalError, PaymentFinalizationError, ValueError) as exc:
        return render(request, "billing/payment_result.html", {
            "success": False, "message": f"تأیید پرداخت انجام نشد: {exc}",
            "order": attempt.order,
        }, status=400)


@login_required
@require_POST
def pay_existing_order(request, order_number):
    """Start a real Zarinpal attempt for the signed-in user's pending order."""
    order = get_object_or_404(
        PaymentOrder.objects.select_related("plan", "plan__product"),
        order_number=order_number,
        user=request.user,
        status=PaymentOrder.Status.PENDING,
    )
    if not getattr(settings, "ZARINPAL_ENABLED", True):
        messages.error(request, "درگاه زرین‌پال در حال حاضر غیرفعال است.")
        return redirect("portal:orders")
    try:
        amount = amount_in_rials(order.amount_minor_units, order.currency)
        attempt = create_payment_attempt(
            user=request.user,
            order_id=order.pk,
            provider="zarinpal",
            idempotency_key=uuid.uuid4(),
        )
        callback_url = request.build_absolute_uri(reverse("billing:zarinpal_callback"))
        authority, payment_url = request_payment(
            amount=amount,
            description=f"Nebula Vault order {order.order_number}",
            callback_url=callback_url,
            email=getattr(request.user, "email", None),
        )
        attempt.provider_reference = authority
        attempt.status = PaymentAttempt.Status.PENDING
        attempt.save(update_fields=["provider_reference", "status", "updated_at"])
        return redirect(payment_url)
    except (PaymentAttemptCreationError, ZarinpalError, ValueError) as exc:
        messages.error(request, f"شروع پرداخت سفارش ممکن نشد: {exc}")
        return redirect("portal:orders")
