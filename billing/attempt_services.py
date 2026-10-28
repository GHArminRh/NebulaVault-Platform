"""Create idempotent payment attempts for pending orders."""

from uuid import UUID

from django.db import IntegrityError, transaction

from .models import PaymentAttempt, PaymentOrder
from .services import PaymentAttemptCreationError, PaymentAttemptIdempotencyConflict


def create_payment_attempt(
    *,
    user,
    order_id,
    provider,
    idempotency_key,
):
    """
    Create or return an idempotent payment attempt.

    Repeated requests for the same order and provider return the same
    attempt. Reusing the request key with another provider is rejected.
    This function never confirms a payment.
    """
    if not user.pk or not user.is_active:
        raise PaymentAttemptCreationError(
            "برای ادامه، حساب کاربری فعال و ذخیره‌شده لازم است."
        )

    if not isinstance(provider, str):
        raise PaymentAttemptCreationError("ارائه‌دهنده پرداخت معتبر الزامی است.")

    provider = provider.strip().lower()

    if not provider or len(provider) > 40:
        raise PaymentAttemptCreationError("ارائه‌دهنده پرداخت معتبر الزامی است.")

    try:
        key = UUID(str(idempotency_key))
    except (TypeError, ValueError, AttributeError):
        raise PaymentAttemptCreationError(
            "کلید معتبر برای جلوگیری از ثبت تکراری الزامی است."
        ) from None

    try:
        order_pk = UUID(str(order_id))
    except (TypeError, ValueError, AttributeError):
        raise PaymentAttemptCreationError(
            "سفارش معتبر الزامی است."
        ) from None

    try:
        with transaction.atomic():
            order = (
                PaymentOrder.objects
                .select_for_update()
                .filter(pk=order_pk, user=user)
                .first()
            )

            if order is None:
                raise PaymentAttemptCreationError(
                    "سفارش مربوط به این کاربر پیدا نشد."
                )

            existing = PaymentAttempt.objects.filter(
                order=order,
                request_key=key,
            ).first()

            if existing:
                if existing.provider != provider:
                    raise PaymentAttemptIdempotencyConflict(
                        "این کلید درخواست برای ارائه‌دهنده دیگری استفاده شده است."
                    )
                return existing

            if order.status != PaymentOrder.Status.PENDING:
                raise PaymentAttemptCreationError(
                    "فقط برای سفارش‌های در انتظار می‌توان تلاش پرداخت ایجاد کرد."
                )

            return PaymentAttempt.objects.create(
                order=order,
                request_key=key,
                provider=provider,
                amount_minor_units=order.amount_minor_units,
                currency=order.currency,
                status=PaymentAttempt.Status.CREATED,
            )

    except IntegrityError:
        # A concurrent request may have created the same attempt.
        existing = PaymentAttempt.objects.filter(
            order_id=order_pk,
            order__user=user,
            request_key=key,
        ).first()

        if existing:
            if existing.provider != provider:
                raise PaymentAttemptIdempotencyConflict(
                    "این کلید درخواست برای ارائه‌دهنده دیگری استفاده شده است."
                ) from None
            return existing

        raise
