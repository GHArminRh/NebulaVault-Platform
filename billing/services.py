
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone

from catalog.models import Plan
from subscriptions.models import Subscription, SubscriptionRenewal
from subscriptions.services import _add_plan_duration

from .models import PaymentAttempt, PaymentOrder


def _is_provider_reference_integrity_error(exc):
    """Return whether an IntegrityError identifies a provider-reference clash."""
    cause = exc.__cause__
    diagnostic = getattr(cause, "diag", None)

    table_name = getattr(diagnostic, "table_name", None)
    column_name = getattr(diagnostic, "column_name", None)
    if (table_name, column_name) in {
        ("billing_paymentattempt", "provider_reference"),
        ("subscriptions_subscriptionrenewal", "payment_reference"),
    }:
        return True

    constraint_name = getattr(diagnostic, "constraint_name", None)
    if constraint_name in {
        "billing_paymentattempt_provider_reference_key",
        "subscriptions_subscriptionrenewal_payment_reference_key",
    }:
        return True

    message = str(cause or exc).lower()
    sqlite_unique_errors = (
        "unique constraint failed: billing_paymentattempt.provider_reference",
        "unique constraint failed: subscriptions_subscriptionrenewal.payment_reference",
    )
    if any(marker in message for marker in sqlite_unique_errors):
        return True

    # MySQL/MariaDB report duplicate-key violations in the exception text.
    return (
        "duplicate entry" in message
        and "for key" in message
        and (
            "provider_reference" in message
            or "payment_reference" in message
        )
    )


class OrderCreationError(Exception):
    """The requested payment order cannot be created."""


class IdempotencyConflict(OrderCreationError):
    """An idempotency key was reused for a different request."""


class PaymentAttemptCreationError(Exception):
    """The requested payment attempt cannot be created."""


class PaymentAttemptIdempotencyConflict(PaymentAttemptCreationError):
    """An idempotency key was reused for a different request."""


class PaymentFinalizationError(Exception):
    """A verified payment cannot be finalized."""


class PaymentReferenceConflict(PaymentFinalizationError):
    """A provider payment reference was reused inconsistently."""


def create_payment_order(
    *,
    user,
    plan_id,
    idempotency_key,
    subscription_id=None,
):
    """
    Create an order using the server-side plan price.

    If subscription_id is omitted, automatically select the user's sole
    non-canceled paid subscription for this product and plan. If none
    exists, create an initial-purchase order. Ambiguous selections fail.

    A different idempotency key cannot create a second pending order
    for the same initial purchase or subscription renewal.
    """
    if not user.pk or not user.is_active:
        raise OrderCreationError("An active, saved user is required.")

    try:
        key = UUID(str(idempotency_key))
    except (TypeError, ValueError, AttributeError):
        raise OrderCreationError(
            "A valid idempotency key is required."
        ) from None

    try:
        if isinstance(plan_id, bool):
            raise ValueError
        plan_pk = int(plan_id)
    except (TypeError, ValueError, OverflowError):
        raise OrderCreationError("A valid plan is required.") from None

    if plan_pk <= 0:
        raise OrderCreationError("A valid plan is required.")

    subscription_pk = None
    if subscription_id is not None:
        try:
            if isinstance(subscription_id, bool):
                raise ValueError
            subscription_pk = int(subscription_id)
        except (TypeError, ValueError, OverflowError):
            raise OrderCreationError(
                "A valid subscription is required."
            ) from None

        if subscription_pk <= 0:
            raise OrderCreationError("A valid subscription is required.")

    subscription_was_explicit = subscription_pk is not None

    try:
        with transaction.atomic():
            # Serialize order creation for this user.
            from accounts.models import Customer

            UserModel = Customer
            locked_user = (
                UserModel.objects
                .select_for_update()
                .filter(pk=user.pk, is_active=True)
                .first()
            )
            if locked_user is None:
                raise OrderCreationError(
                    "An active, saved user is required."
                )

            existing = (
                PaymentOrder.objects
                .select_for_update()
                .filter(user=locked_user, idempotency_key=key)
                .first()
            )

            if existing:
                if existing.plan_id != plan_pk:
                    raise IdempotencyConflict(
                        "This idempotency key was used for a different order."
                    )

                if (
                    existing.subscription_id_was_explicit is not None
                    and existing.subscription_id_was_explicit
                    != subscription_was_explicit
                ):
                    raise IdempotencyConflict(
                        "This idempotency key was used for a different request."
                    )

                if (
                    subscription_pk is not None
                    and existing.subscription_id != subscription_pk
                ):
                    raise IdempotencyConflict(
                        "This idempotency key was used for a different order."
                    )

                return existing

            plan = (
                Plan.objects
                .select_for_update()
                .select_related("product")
                .filter(
                    pk=plan_pk,
                    is_active=True,
                    product__is_active=True,
                )
                .first()
            )

            if plan is None:
                raise OrderCreationError(
                    "The selected plan is unavailable."
                )

            if plan.price_minor_units <= 0:
                raise OrderCreationError(
                    "The selected plan has an invalid price."
                )

            if subscription_pk is not None:
                subscription = (
                    Subscription.objects
                    .select_for_update()
                    .filter(pk=subscription_pk, user=locked_user)
                    .first()
                )

                if subscription is None:
                    raise OrderCreationError(
                        "The subscription was not found for this user."
                    )

                if subscription.kind != Subscription.Kind.PAID:
                    raise OrderCreationError(
                        "Trial subscriptions cannot be renewed."
                    )

                if subscription.status == Subscription.Status.CANCELED:
                    raise OrderCreationError(
                        "Canceled subscriptions cannot be renewed."
                    )

                if (
                    subscription.product_id != plan.product_id
                    or subscription.plan_id != plan.pk
                ):
                    raise OrderCreationError(
                        "The plan does not match the subscription."
                    )
            else:
                candidates = list(
                    Subscription.objects
                    .select_for_update()
                    .filter(
                        user=locked_user,
                        product_id=plan.product_id,
                        plan_id=plan.pk,
                        kind=Subscription.Kind.PAID,
                    )
                    .exclude(status=Subscription.Status.CANCELED)
                    .order_by("pk")[:2]
                )

                if len(candidates) > 1:
                    raise OrderCreationError(
                        "Multiple paid subscriptions match this product "
                        "and plan. Specify subscription_id explicitly."
                    )

                subscription = candidates[0] if candidates else None

            # A pending initial purchase blocks another initial purchase
            # for the same user and plan. A pending renewal blocks another
            # renewal of the same subscription.
            pending_orders = PaymentOrder.objects.filter(
                user=locked_user,
                plan=plan,
                status=PaymentOrder.Status.PENDING,
            )

            if subscription is None:
                pending_orders = pending_orders.filter(
                    subscription__isnull=True
                )
            else:
                pending_orders = pending_orders.filter(
                    subscription=subscription
                )

            if pending_orders.exists():
                raise OrderCreationError(
                    "A pending payment order already exists for this purchase. "
                    "Continue with the existing order or wait until it is "
                    "canceled or expired."
                )

            return PaymentOrder.objects.create(
                user=locked_user,
                plan=plan,
                subscription=subscription,
                idempotency_key=key,
                subscription_id_was_explicit=subscription_was_explicit,
                amount_minor_units=plan.price_minor_units,
                currency=plan.currency,
                status=PaymentOrder.Status.PENDING,
            )

    except IntegrityError:
        existing = PaymentOrder.objects.filter(
            user=user,
            idempotency_key=key,
        ).first()

        if existing:
            if existing.plan_id != plan_pk:
                raise IdempotencyConflict(
                    "This idempotency key was used for a different order."
                ) from None

            if (
                existing.subscription_id_was_explicit is not None
                and existing.subscription_id_was_explicit
                != subscription_was_explicit
            ):
                raise IdempotencyConflict(
                    "This idempotency key was used for a different request."
                ) from None

            if (
                subscription_pk is not None
                and existing.subscription_id != subscription_pk
            ):
                raise IdempotencyConflict(
                    "This idempotency key was used for a different order."
                ) from None

            return existing

        raise


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
            "An active, saved user is required."
        )

    if not isinstance(provider, str):
        raise PaymentAttemptCreationError("A valid provider is required.")

    provider = provider.strip().lower()

    if not provider or len(provider) > 40:
        raise PaymentAttemptCreationError("A valid provider is required.")

    try:
        key = UUID(str(idempotency_key))
    except (TypeError, ValueError, AttributeError):
        raise PaymentAttemptCreationError(
            "A valid idempotency key is required."
        ) from None

    try:
        if isinstance(order_id, bool):
            raise ValueError
        order_pk = int(order_id)
    except (TypeError, ValueError, OverflowError):
        raise PaymentAttemptCreationError(
            "A valid order is required."
        ) from None

    if order_pk <= 0:
        raise PaymentAttemptCreationError("A valid order is required.")

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
                    "The order was not found for this user."
                )

            existing = PaymentAttempt.objects.filter(
                order=order,
                request_key=key,
            ).first()

            if existing:
                if existing.provider != provider:
                    raise PaymentAttemptIdempotencyConflict(
                        "This request key was used with another provider."
                    )
                return existing

            if order.status != PaymentOrder.Status.PENDING:
                raise PaymentAttemptCreationError(
                    "Only pending orders can start a payment attempt."
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
                    "This request key was used with another provider."
                ) from None
            return existing

        raise


def finalize_payment(
    *,
    attempt_id,
    provider_reference,
    confirmed_amount_minor_units,
    confirmed_currency,
):
    """
    Finalize a payment after trusted server-side provider verification.

    Never call this function with unverified browser-supplied payment data.
    """
    if not isinstance(provider_reference, str):
        raise PaymentFinalizationError(
            "A valid provider reference is required."
        )

    provider_reference = provider_reference.strip()
    if not provider_reference or len(provider_reference) > 255:
        raise PaymentFinalizationError(
            "A valid provider reference is required."
        )

    if (
        isinstance(confirmed_amount_minor_units, bool)
        or not isinstance(confirmed_amount_minor_units, int)
        or confirmed_amount_minor_units <= 0
    ):
        raise PaymentFinalizationError("The confirmed amount is invalid.")

    if not isinstance(confirmed_currency, str):
        raise PaymentFinalizationError("The confirmed currency is invalid.")

    confirmed_currency = confirmed_currency.strip().upper()
    if (
        len(confirmed_currency) != 3
        or not confirmed_currency.isascii()
        or not confirmed_currency.isalpha()
    ):
        raise PaymentFinalizationError("The confirmed currency is invalid.")

    try:
        if isinstance(attempt_id, bool):
            raise ValueError
        attempt_pk = int(attempt_id)
    except (TypeError, ValueError, OverflowError):
        raise PaymentFinalizationError(
            "A valid payment attempt is required."
        ) from None

    if attempt_pk <= 0:
        raise PaymentFinalizationError(
            "A valid payment attempt is required."
        )

    order_id = (
        PaymentAttempt.objects
        .filter(pk=attempt_pk)
        .values_list("order_id", flat=True)
        .first()
    )

    if order_id is None:
        raise PaymentFinalizationError(
            "The payment attempt was not found."
        )

    try:
        with transaction.atomic():
            order = (
                PaymentOrder.objects
                .select_for_update()
                .select_related("plan__product")
                .get(pk=order_id)
            )
            attempt = (
                PaymentAttempt.objects
                .select_for_update()
                .get(pk=attempt_pk, order_id=order.pk)
            )

            # An already completed callback must be idempotent.
            if (
                attempt.status == PaymentAttempt.Status.SUCCEEDED
                and order.status == PaymentOrder.Status.PAID
            ):
                if (
                    attempt.provider_reference == provider_reference
                    and attempt.amount_minor_units
                    == confirmed_amount_minor_units
                    and attempt.currency == confirmed_currency
                    and order.amount_minor_units
                    == confirmed_amount_minor_units
                    and order.currency == confirmed_currency
                ):
                    return attempt

                raise PaymentReferenceConflict(
                    "This payment was already finalized with different details."
                )

            if attempt.status not in {
                PaymentAttempt.Status.CREATED,
                PaymentAttempt.Status.PENDING,
            }:
                raise PaymentFinalizationError(
                    "This payment attempt cannot be finalized."
                )

            if order.status != PaymentOrder.Status.PENDING:
                raise PaymentFinalizationError(
                    "Only pending orders can be finalized."
                )

            if (
                attempt.amount_minor_units != order.amount_minor_units
                or attempt.currency != order.currency
            ):
                raise PaymentFinalizationError(
                    "The payment attempt does not match its order."
                )

            if (
                confirmed_amount_minor_units != order.amount_minor_units
                or confirmed_currency != order.currency
            ):
                raise PaymentFinalizationError(
                    "The confirmed payment does not match the order."
                )

            if attempt.provider_reference not in (None, provider_reference):
                raise PaymentReferenceConflict(
                    "This attempt already has another provider reference."
                )

            now = timezone.now()
            plan = order.plan

            if order.subscription_id is None:
                # Initial purchase: create one paid subscription.
                subscription = Subscription.objects.create(
                    user=order.user,
                    product=plan.product,
                    kind=Subscription.Kind.PAID,
                    status=Subscription.Status.ACTIVE,
                    plan=plan,
                    trial_redemption=None,
                    starts_at=now,
                    expires_at=_add_plan_duration(now, plan),
                )
                order.subscription = subscription
            else:
                # Renewal: lock and validate the existing subscription.
                subscription = (
                    Subscription.objects
                    .select_for_update()
                    .get(pk=order.subscription_id)
                )

                if subscription.user_id != order.user_id:
                    raise PaymentFinalizationError(
                        "The subscription does not belong to this customer."
                    )

                if subscription.kind != Subscription.Kind.PAID:
                    raise PaymentFinalizationError(
                        "Trial subscriptions cannot be renewed."
                    )

                if subscription.status == Subscription.Status.CANCELED:
                    raise PaymentFinalizationError(
                        "Canceled subscriptions cannot be renewed."
                    )

                if (
                    subscription.plan_id != plan.pk
                    or subscription.product_id != plan.product_id
                ):
                    raise PaymentFinalizationError(
                        "The order plan does not match the subscription."
                    )

                previous_expiry = subscription.expires_at
                extension_start = max(previous_expiry, now)
                new_expiry = _add_plan_duration(extension_start, plan)

                SubscriptionRenewal.objects.create(
                    subscription=subscription,
                    payment_reference=provider_reference,
                    previous_expires_at=previous_expiry,
                    new_expires_at=new_expiry,
                    amount_minor_units=order.amount_minor_units,
                    currency=order.currency,
                )

                subscription.expires_at = new_expiry
                subscription.status = Subscription.Status.ACTIVE
                subscription.save(
                    update_fields=["expires_at", "status", "updated_at"]
                )

            attempt.status = PaymentAttempt.Status.SUCCEEDED
            attempt.provider_reference = provider_reference
            attempt.confirmed_at = now
            attempt.save(
                update_fields=[
                    "status",
                    "provider_reference",
                    "confirmed_at",
                    "updated_at",
                ]
            )

            order.status = PaymentOrder.Status.PAID
            order.paid_at = now
            order.save(
                update_fields=[
                    "status",
                    "paid_at",
                    "subscription",
                    "updated_at",
                ]
            )

            return attempt

    except PaymentAttempt.DoesNotExist:
        raise PaymentFinalizationError(
            "The payment attempt was not found."
        ) from None
    except PaymentOrder.DoesNotExist:
        raise PaymentFinalizationError(
            "The payment order was not found."
        ) from None
    except Subscription.DoesNotExist:
        raise PaymentFinalizationError(
            "The subscription was not found."
        ) from None
    except IntegrityError as exc:
        # Do not mask unrelated check, foreign-key, or uniqueness failures.
        if not _is_provider_reference_integrity_error(exc):
            raise

        existing = (
            PaymentAttempt.objects
            .select_related("order")
            .filter(provider_reference=provider_reference)
            .first()
        )

        if existing is not None and existing.pk != attempt_pk:
            raise PaymentReferenceConflict(
                "This provider reference has already been used."
            ) from None

        # A concurrent retry may have completed this exact attempt.
        if (
            existing is not None
            and existing.pk == attempt_pk
            and existing.status == PaymentAttempt.Status.SUCCEEDED
            and existing.provider_reference == provider_reference
            and existing.amount_minor_units == confirmed_amount_minor_units
            and existing.currency == confirmed_currency
            and existing.order.status == PaymentOrder.Status.PAID
            and existing.order.amount_minor_units
            == confirmed_amount_minor_units
            and existing.order.currency == confirmed_currency
        ):
            return existing

        # A renewal record may own the reference even if no attempt does.
        renewal_exists = SubscriptionRenewal.objects.filter(
            payment_reference=provider_reference,
        ).exists()

        if renewal_exists:
            raise PaymentReferenceConflict(
                "This provider reference has already been used."
            ) from None

        # The unique violation was not attributable to an existing reference.
        raise
