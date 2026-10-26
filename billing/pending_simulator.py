"""Start the local simulator for an already-created pending order."""
import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import PaymentAttempt, PaymentOrder
from .services import PaymentAttemptCreationError, create_payment_attempt


def _disabled(request):
    return render(request, "billing/payment_result.html", {
        "success": False,
        "message": "شبیه‌ساز پرداخت فقط در محیط توسعه و با فعال‌بودن پرداخت آزمایشی در دسترس است.",
    }, status=404)


@login_required
@require_POST
def start_pending_order_simulation(request, order_id):
    if not (settings.DEBUG and getattr(settings, "NEBULA_MOCK_PAYMENTS", False)):
        return _disabled(request)

    order = get_object_or_404(
        PaymentOrder.objects.select_related("plan", "plan__product"),
        pk=order_id,
        user=request.user,
        status=PaymentOrder.Status.PENDING,
    )
    if not order.plan.is_active or not order.plan.product.is_active:
        return render(request, "billing/payment_result.html", {
            "success": False,
            "message": "این طرح دیگر برای پرداخت در دسترس نیست.",
        }, status=400)

    attempt = PaymentAttempt.objects.filter(
        order=order,
        provider="local_simulator",
        status__in=(PaymentAttempt.Status.CREATED, PaymentAttempt.Status.PENDING),
    ).order_by("-created_at").first()
    if attempt is None:
        try:
            attempt = create_payment_attempt(
                user=request.user,
                order_id=order.pk,
                provider="local_simulator",
                idempotency_key=uuid.uuid4(),
            )
        except (PaymentAttemptCreationError, ValueError):
            return render(request, "billing/payment_result.html", {
                "success": False,
                "message": "شروع شبیه‌سازی پرداخت ممکن نشد. دوباره تلاش کن.",
            }, status=400)

    if not attempt.provider_reference:
        attempt.provider_reference = f"local-sim-{attempt.pk}"
    if attempt.status == PaymentAttempt.Status.CREATED:
        attempt.status = PaymentAttempt.Status.PENDING
    attempt.save(update_fields=["provider_reference", "status", "updated_at"])
    return redirect("billing:local_simulator", attempt_id=attempt.pk)
