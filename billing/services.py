
from uuid import UUID

from django.db import IntegrityError, transaction

from catalog.models import Plan

from .models import PaymentAttempt, PaymentOrder


class OrderCreationError(Exception):
    """The requested payment order cannot be created."""


class IdempotencyConflict(OrderCreationError):
    """An idempotency key was reused for a different request."""


class PaymentAttemptCreationError(Exception):
    """The requested payment attempt cannot be created."""


def create_payment_order(*, user, plan_id, idempotency_key):
    """
    Create an order using the current server-side plan price.

    Repeating the same request for the same user returns the existing
    order. Reusing its key for a different plan raises a conflict.
    """

    if not user.pk or not user.is_active:
        raise OrderCreationError("An active, saved user is required.")

    try:
        key = UUID(str(idempotency_key))
    except (TypeError, ValueError, AttributeError):
        raise OrderCreationError("A valid idempotency key is required.") from None

    try:
        plan_pk = int(plan_id)
    except (TypeError, ValueError, OverflowError):
        raise OrderCreationError("A valid plan is required.") from None

    if plan_pk <= 0:
        raise OrderCreationError("A valid plan is required.")

    try:
        with transaction.atomic():
            existing = (
                PaymentOrder.objects
                .select_for_update()
                .filter(user=user, idempotency_key=key)
                .first()
            )

            if existing:
                if existing.plan_id != plan_pk:
                    raise IdempotencyConflict(
                        "This idempotency key was used for another plan."
                    )
                return existing

            plan = (
                Plan.objects
                .select_for_update()
                .select_related("product")
                .filter(pk=plan_pk, is_active=True, product__is_active=True)
                .first()
            )

            if plan is None:
                raise OrderCreationError("The selected plan is unavailable.")

            if plan.price_minor_units <= 0:
                raise OrderCreationError("The selected plan has an invalid price.")

            order = PaymentOrder.objects.create(
                user=user,
                plan=plan,
                idempotency_key=key,
                amount_minor_units=plan.price_minor_units,
                currency=plan.currency,
                status=PaymentOrder.Status.PENDING,
            )

            return order

    except IntegrityError:
        # A concurrent request may have inserted the same key.
        existing = PaymentOrder.objects.filter(
            user=user,
            idempotency_key=key,
        ).first()

        if existing:
            if existing.plan_id != plan_pk:
                raise IdempotencyConflict(
                    "This idempotency key was used for another plan."
                ) from None
            return existing

        raise


def create_payment_attempt(*, user, order_id, provider):
    """
    Create a payment attempt for an order owned by the given user.

    This function does not contact a provider or confirm a payment.
    """

    if not user.pk or not user.is_active:
        raise PaymentAttemptCreationError(
            "An active, saved user is required."
        )

    if not isinstance(provider, str):
        raise PaymentAttemptCreationError("A valid provider is required.")

    provider = provider.strip().lower()

    if not provider or len(provider) > 40:
        raise PaymentAttemptCreationError("A valid provider is required.")

    try:
        order_pk = int(order_id)
    except (TypeError, ValueError, OverflowError):
        raise PaymentAttemptCreationError("A valid order is required.") from None

    if order_pk <= 0:
        raise PaymentAttemptCreationError("A valid order is required.")

    with transaction.atomic():
        order = (
            PaymentOrder.objects
            .select_for_update()
            .filter(pk=order_pk, user=user)
            .first()
        )

        if order is None:
            raise PaymentAttemptCreationError(
                "The order was not found for this user."
            )

        if order.status != PaymentOrder.Status.PENDING:
            raise PaymentAttemptCreationError(
                "Only pending orders can start a payment attempt."
            )

        attempt = PaymentAttempt.objects.create(
            order=order,
            provider=provider,
            amount_minor_units=order.amount_minor_units,
            currency=order.currency,
            status=PaymentAttempt.Status.CREATED,
        )

        return attempt
