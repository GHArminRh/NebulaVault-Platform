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


def _ga4_purchase_payload(order):
    """Build a PII-free GA4 purchase payload from a server-verified paid order."""
    currency = (order.currency or "").upper()
    divisor = 10 if currency == "IRT" else 100
    analytics_currency = "IRR" if currency == "IRT" else currency

    lines = list(order.items.select_related("plan").all())
    items = []
    if lines:
        for line in lines:
            items.append({
                "item_id": str(line.plan_id),
                "item_name": line.plan_name,
                "item_category": line.product_name,
                "price": round(line.amount_minor_units / divisor, 2),
                "quantity": 1,
            })
    else:
        plan = order.plan
        items.append({
            "item_id": str(plan.pk),
            "item_name": plan.name,
            "item_category": plan.product.name,
            "price": round(order.amount_minor_units / divisor, 2),
            "quantity": 1,
        })

    return {
        "transaction_id": str(order.order_number),
        "value": round(order.amount_minor_units / divisor, 2),
        "currency": analytics_currency,
        "items": items,
    }


def _replace_stale_single_plan_order(order, user):
    """Cancel an unpaid single-plan order when its catalog price has changed.

    Orders remain immutable snapshots. Instead of changing an order or attempt
    amount in place, create a fresh order at the current catalog price. Only
    attempts that never obtained a provider reference can be safely canceled.
    Cart orders and subscription renewals retain their own snapshot semantics.
    """
    with transaction.atomic():
        locked_order = (
            PaymentOrder.objects.select_for_update()
            .select_related("plan")
            .get(pk=order.pk, user=user)
        )
        if (
            locked_order.status != PaymentOrder.Status.PENDING
            or locked_order.subscription_id is not None
            or locked_order.items.exists()
        ):
            return locked_order

        plan = Plan.objects.select_for_update().get(pk=locked_order.plan_id)
        if (
            locked_order.amount_minor_units == plan.price_minor_units
            and locked_order.currency.upper() == plan.currency.upper()
        ):
            return locked_order

        attempts = list(locked_order.payment_attempts.select_for_update().all())
        safe_to_cancel = {
            PaymentAttempt.Status.CREATED,
            PaymentAttempt.Status.FAILED,
            PaymentAttempt.Status.CANCELED,
        }
        if any(
            attempt.provider_reference
            or attempt.status not in safe_to_cancel
            for attempt in attempts
        ):
            raise PaymentAttemptCreationError(
                "قیمت طرح تغییر کرده، اما سفارش قبلی یک تلاش پرداخت فعال یا دارای شناسه درگاه دارد. "
                "برای جلوگیری از پرداخت با مبلغ نادرست، این سفارش به‌طور خودکار جایگزین نشد."
            )

        for attempt in attempts:
            if attempt.status != PaymentAttempt.Status.CANCELED:
                attempt.status = PaymentAttempt.Status.CANCELED
                attempt.save(update_fields=["status", "updated_at"])

        locked_order.status = PaymentOrder.Status.CANCELED
        locked_order.save(update_fields=["status", "updated_at"])

        return create_payment_order(
            user=user,
            plan_id=plan.pk,
            idempotency_key=uuid.uuid4(),
        )


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
        else:
            order = _replace_stale_single_plan_order(order, request.user)
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
            "analytics_purchase": _ga4_purchase_payload(attempt.order),
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
        original_order_id = order.pk
        order = _replace_stale_single_plan_order(order, request.user)
        if order.pk != original_order_id:
            messages.info(
                request,
                "قیمت طرح تغییر کرده بود؛ سفارش قبلی لغو و سفارش تازه با قیمت فعلی ساخته شد. "
                "لطفاً سفارش جدید را در فهرست سفارش‌ها پرداخت کنید.",
            )
            return redirect("portal:orders")
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
