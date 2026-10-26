"""ZarinPal payment initiation and server-verified callback handling."""
import logging
from urllib.parse import urlencode, urljoin
from uuid import UUID

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import PaymentAttempt, PaymentOrder
from .services import (
    OrderCreationError,
    PaymentAttemptCreationError,
    PaymentAttemptIdempotencyConflict,
    PaymentFinalizationError,
    PaymentReferenceConflict,
    create_payment_attempt,
    finalize_payment,
)
from .zarinpal_gateway import (
    ZarinPalGatewayError,
    request_payment,
    validate_callback_url,
    verify_payment,
)

logger = logging.getLogger(__name__)


def _payment_result(request, *, title, message, order=None, status=200):
    return render(
        request,
        "portal/payment_result.html",
        {
            "page_title": title,
            "result_message": message,
            "order_number": str(order.order_number) if order else "",
        },
        status=status,
    )


def _zarinpal_is_available():
    return (
        bool(getattr(settings, "ZARINPAL_ENABLED", False))
        and not getattr(settings, "NEBULA_MOCK_PAYMENTS", settings.DEBUG)
    )


@login_required
@require_POST
def zarinpal_start(request, order_id):
    """Start or resume a ZarinPal attempt for an order owned by this user."""
    if not _zarinpal_is_available():
        messages.error(request, "درگاه زرین‌پال فعال نیست یا پرداخت آزمایشی هنوز روشن است.")
        return redirect("portal:orders")

    order = get_object_or_404(
        PaymentOrder.objects.select_related("plan", "plan__product"),
        pk=order_id,
        user=request.user,
    )
    if order.status != PaymentOrder.Status.PENDING:
        messages.error(request, "این سفارش در وضعیت قابل پرداخت نیست.")
        return redirect("portal:orders")

    # ZarinPal's payment amount is in IRR, not Toman or a generic minor unit.
    if order.currency != "IRR" or order.amount_minor_units < 1000:
        messages.error(
            request,
            "برای پرداخت با زرین‌پال، واحد پول طرح باید IRR و مبلغ آن دست‌کم ۱۰۰۰ ریال باشد.",
        )
        return redirect("portal:orders")

    try:
        # Serialize attempts for a single order. Reuse any still-usable ZarinPal
        # attempt instead of creating another transaction when the customer
        # double-clicks, reloads the page, or retries after returning from the bank.
        with transaction.atomic():
            locked_order = (
                PaymentOrder.objects.select_for_update()
                .filter(pk=order.pk, user=request.user, status=PaymentOrder.Status.PENDING)
                .first()
            )
            if locked_order is None:
                messages.error(request, "این سفارش دیگر در وضعیت قابل پرداخت نیست.")
                return redirect("portal:orders")

            attempt = (
                PaymentAttempt.objects.select_for_update()
                .filter(
                    order=locked_order,
                    provider="zarinpal",
                    status__in=[
                        PaymentAttempt.Status.CREATED,
                        PaymentAttempt.Status.PENDING,
                    ],
                )
                .order_by("-created_at")
                .first()
            )
            if attempt is None:
                attempt = create_payment_attempt(
                    user=request.user,
                    order_id=locked_order.pk,
                    provider="zarinpal",
                    idempotency_key=request.POST.get("request_key") or "",
                )
    except (PaymentAttemptCreationError, PaymentAttemptIdempotencyConflict) as exc:
        messages.error(request, str(exc))
        return redirect("portal:orders")
    except Exception:
        logger.exception("Could not create ZarinPal payment attempt")
        messages.error(request, "ایجاد درخواست پرداخت ممکن نشد. دوباره تلاش کنید.")
        return redirect("portal:orders")

    gateway_error = None
    payment_url = None
    try:
        # Lock the attempt while the remote request is made. If a browser retries
        # the same form, it will reuse the same authority instead of opening a
        # second provider transaction for the same attempt.
        with transaction.atomic():
            attempt = (
                PaymentAttempt.objects.select_for_update()
                .select_related("order", "order__user", "order__plan", "order__plan__product")
                .get(pk=attempt.pk, order__user=request.user)
            )
            if attempt.status == PaymentAttempt.Status.SUCCEEDED:
                return redirect("portal:orders")
            if attempt.provider != "zarinpal":
                raise ZarinPalGatewayError("تلاش پرداخت متعلق به درگاه زرین‌پال نیست.")

            if attempt.provider_reference:
                client_url = _existing_payment_url(attempt.provider_reference)
                payment_url = client_url
            elif attempt.status in {
                PaymentAttempt.Status.CANCELED,
                PaymentAttempt.Status.REFUNDED,
            }:
                gateway_error = "این تلاش پرداخت دیگر قابل استفاده نیست؛ یک درخواست تازه بسازید."
            else:
                callback_path = reverse("billing:zarinpal_callback")
                configured_base = getattr(settings, "ZARINPAL_PUBLIC_BASE_URL", "")
                if configured_base:
                    callback_url = urljoin(configured_base.rstrip("/") + "/", callback_path.lstrip("/"))
                else:
                    callback_url = request.build_absolute_uri(callback_path)
                callback_url = validate_callback_url(
                    callback_url + "?" + urlencode({"attempt_id": str(attempt.pk)})
                )

                try:
                    authority, payment_url = request_payment(
                        amount_irr=attempt.amount_minor_units,
                        callback_url=callback_url,
                        description=(
                            f"Nebula Vault: {attempt.order.plan.product.name} — "
                            f"{attempt.order.plan.name} — {attempt.order.order_number}"
                        ),
                        email=getattr(attempt.order.user, "email", ""),
                    )
                    attempt.provider_reference = authority
                    attempt.status = PaymentAttempt.Status.PENDING
                    attempt.save(
                        update_fields=["provider_reference", "status", "updated_at"]
                    )
                except ZarinPalGatewayError as exc:
                    attempt.status = PaymentAttempt.Status.FAILED
                    attempt.save(update_fields=["status", "updated_at"])
                    gateway_error = str(exc)
    except PaymentAttempt.DoesNotExist:
        raise Http404("Payment attempt not found")
    except ZarinPalGatewayError as exc:
        gateway_error = str(exc)
    except Exception:
        logger.exception("Unexpected error starting ZarinPal payment")
        gateway_error = "ارتباط با درگاه پرداخت برقرار نشد. لطفاً دوباره تلاش کنید."

    if gateway_error:
        messages.error(request, gateway_error)
        return redirect("portal:orders")
    if not payment_url:
        messages.error(request, "نشانی ورود به درگاه پرداخت ساخته نشد.")
        return redirect("portal:orders")
    return redirect(payment_url)


def _existing_payment_url(authority):
    """Regenerate the official hosted checkout URL for a known authority."""
    # Use the SDK's public URL builder so sandbox/production host selection
    # stays aligned with the active ZarinPal configuration.
    from .zarinpal_gateway import _client

    return _client().payments.generate_payment_url(authority)


@require_GET
def zarinpal_callback(request):
    """Verify a ZarinPal return on the server before finalizing the order."""
    attempt_id_raw = request.GET.get("attempt_id", "")
    authority = request.GET.get("Authority", "")
    provider_status = request.GET.get("Status", "")

    try:
        attempt_id = UUID(attempt_id_raw)
    except (TypeError, ValueError, AttributeError):
        return _payment_result(
            request,
            title="درخواست پرداخت نامعتبر",
            message="شناسه تلاش پرداخت معتبر نیست. وضعیت سفارش را از صفحه سفارش‌ها بررسی کنید.",
            status=400,
        )

    attempt = (
        PaymentAttempt.objects.select_related(
            "order", "order__user", "order__plan", "order__plan__product"
        )
        .filter(pk=attempt_id, provider="zarinpal")
        .first()
    )
    if attempt is None or not attempt.provider_reference or authority != attempt.provider_reference:
        logger.warning("ZarinPal callback did not match a known payment attempt")
        return _payment_result(
            request,
            title="تراکنش قابل شناسایی نیست",
            message="اطلاعات بازگشتی با سفارش ثبت‌شده تطبیق ندارد. در صورت کسر وجه با پشتیبانی تماس بگیرید.",
            status=400,
        )

    order = attempt.order
    if attempt.status == PaymentAttempt.Status.SUCCEEDED and order.status == PaymentOrder.Status.PAID:
        if getattr(request.user, "is_authenticated", False) and request.user.pk == order.user_id:
            return redirect("portal:orders")
        return _payment_result(
            request,
            title="پرداخت قبلاً تأیید شده است",
            message="پرداخت این سفارش قبلاً با موفقیت ثبت شده است. رسید و اطلاعات لایسنس به ایمیل حساب ارسال می‌شود.",
            order=order,
        )

    if provider_status.upper() != "OK":
        # Status is supplied through the user's browser and is not authoritative.
        # Do not mark the attempt failed here: the provider may call back again
        # with a successful result after a retry or delayed browser return.
        return _payment_result(
            request,
            title="پرداخت تکمیل نشد",
            message="زرین‌پال موفقیت پرداخت را در این بازگشت اعلام نکرد. تا تأیید سمت سرور، سفارش پرداخت‌شده نیست؛ وضعیت سفارش را بررسی کنید.",
            order=order,
        )

    if order.currency != "IRR" or attempt.amount_minor_units != order.amount_minor_units:
        logger.error("ZarinPal attempt amount/currency snapshot mismatch for attempt %s", attempt.pk)
        return _payment_result(
            request,
            title="پرداخت نیازمند بررسی است",
            message="مبلغ یا واحد پول تلاش پرداخت با سفارش هم‌خوان نیست. با پشتیبانی تماس بگیرید.",
            order=order,
            status=409,
        )

    try:
        provider_reference = verify_payment(
            amount_irr=attempt.amount_minor_units,
            authority=attempt.provider_reference,
        )
        finalized = finalize_payment(
            attempt_id=attempt.pk,
            provider_reference=provider_reference,
            confirmed_amount_minor_units=attempt.amount_minor_units,
            confirmed_currency=attempt.currency,
        )
    except ZarinPalGatewayError as exc:
        # Preserve the pending state after transient failures; an authenticated
        # retry/callback can safely call verify again (provider code 101 is accepted).
        logger.warning("ZarinPal server-side verification did not complete for attempt %s", attempt.pk)
        return _payment_result(
            request,
            title="تأیید پرداخت در انتظار بررسی",
            message=str(exc),
            order=order,
            status=502,
        )
    except (PaymentFinalizationError, PaymentReferenceConflict) as exc:
        logger.exception("Verified ZarinPal payment could not be finalized for attempt %s", attempt.pk)
        return _payment_result(
            request,
            title="پرداخت نیازمند بررسی است",
            message="درگاه پرداخت بررسی شد، اما ثبت نهایی سفارش تکمیل نشد. شناسه سفارش را برای پشتیبانی نگه دارید.",
            order=order,
            status=409,
        )
    except Exception:
        logger.exception("Unexpected error finalizing ZarinPal callback for attempt %s", attempt.pk)
        return _payment_result(
            request,
            title="پرداخت نیازمند بررسی است",
            message="ثبت نهایی سفارش با خطا مواجه شد. لطفاً شماره سفارش را برای پشتیبانی نگه دارید.",
            order=order,
            status=500,
        )

    # The plaintext key is only placed in the same customer's session once;
    # the billing service sends it by email as well for callbacks without a
    # browser session. Never place a license key into another account's session.
    if (
        getattr(request.user, "is_authenticated", False)
        and request.user.pk == finalized.order.user_id
        and getattr(finalized, "issued_license_key", None)
    ):
        existing = request.session.get("nebula_new_license_keys", {})
        if not isinstance(existing, dict):
            existing = {}
        request.session["nebula_new_license_keys"] = {
            **existing,
            str(finalized.order.order_number): finalized.issued_license_key,
        }

    if getattr(request.user, "is_authenticated", False) and request.user.pk == finalized.order.user_id:
        messages.success(request, "پرداخت زرین‌پال تأیید شد و سفارش شما تکمیل شد.")
        return redirect("portal:orders")

    return _payment_result(
        request,
        title="پرداخت با موفقیت تأیید شد",
        message="پرداخت از سمت سرور تأیید و سفارش ثبت شد. اطلاعات لایسنس به ایمیل حساب خرید ارسال می‌شود.",
        order=finalized.order,
    )
