"""Create immutable single-plan and cart payment-order snapshots."""

import uuid
from uuid import UUID

from django.db import IntegrityError, transaction

from catalog.models import Plan
from subscriptions.models import Subscription

from .models import PaymentOrder, PaymentOrderItem
from .services import IdempotencyConflict, OrderCreationError


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
        raise OrderCreationError("برای ادامه، حساب کاربری فعال و ذخیره‌شده لازم است.")

    try:
        key = UUID(str(idempotency_key))
    except (TypeError, ValueError, AttributeError):
        raise OrderCreationError(
            "کلید معتبر برای جلوگیری از ثبت تکراری الزامی است."
        ) from None

    try:
        plan_pk = UUID(str(plan_id))
    except (TypeError, ValueError, AttributeError):
        raise OrderCreationError("انتخاب طرح معتبر الزامی است.") from None

    subscription_pk = None
    if subscription_id is not None:
        try:
            subscription_pk = UUID(str(subscription_id))
        except (TypeError, ValueError, AttributeError):
            raise OrderCreationError(
                "اشتراک معتبر الزامی است."
            ) from None

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
                    "برای ادامه، حساب کاربری فعال و ذخیره‌شده لازم است."
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
                        "این کلید جلوگیری از ثبت تکراری برای سفارش دیگری استفاده شده است."
                    )

                if (
                    existing.subscription_id_was_explicit is not None
                    and existing.subscription_id_was_explicit
                    != subscription_was_explicit
                ):
                    raise IdempotencyConflict(
                        "این کلید جلوگیری از ثبت تکراری برای درخواست دیگری استفاده شده است."
                    )

                if (
                    subscription_pk is not None
                    and existing.subscription_id != subscription_pk
                ):
                    raise IdempotencyConflict(
                        "این کلید جلوگیری از ثبت تکراری برای سفارش دیگری استفاده شده است."
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
                    "طرح انتخاب‌شده در دسترس نیست."
                )

            if plan.price_minor_units <= 0:
                raise OrderCreationError(
                    "قیمت طرح انتخاب‌شده معتبر نیست."
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
                        "اشتراک مربوط به این کاربر پیدا نشد."
                    )

                if subscription.kind != Subscription.Kind.PAID:
                    raise OrderCreationError(
                        "اشتراک آزمایشی قابل تمدید نیست."
                    )

                if subscription.status == Subscription.Status.CANCELED:
                    raise OrderCreationError(
                        "اشتراک لغوشده قابل تمدید نیست."
                    )

                if (
                    subscription.product_id != plan.product_id
                    or subscription.plan_id != plan.pk
                ):
                    raise OrderCreationError(
                        "طرح انتخاب‌شده با اشتراک مطابقت ندارد."
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
                        "چند اشتراک پولی با این محصول و طرح مطابقت دارند. "
                        "لطفاً اشتراک موردنظر را به‌طور مشخص انتخاب کنید."
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
                    "برای این خرید از قبل سفارش پرداخت در انتظار وجود دارد. "
                    "سفارش فعلی را ادامه دهید یا تا زمان "
                    "لغو یا منقضی‌شدن آن صبر کنید."
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
                    "این کلید جلوگیری از ثبت تکراری برای سفارش دیگری استفاده شده است."
                ) from None

            if (
                existing.subscription_id_was_explicit is not None
                and existing.subscription_id_was_explicit
                != subscription_was_explicit
            ):
                raise IdempotencyConflict(
                    "این کلید جلوگیری از ثبت تکراری برای درخواست دیگری استفاده شده است."
                ) from None

            if (
                subscription_pk is not None
                and existing.subscription_id != subscription_pk
            ):
                raise IdempotencyConflict(
                    "این کلید جلوگیری از ثبت تکراری برای سفارش دیگری استفاده شده است."
                ) from None

            return existing

        raise



def create_cart_payment_order(*, user, plan_ids):
    """Create or reuse one pending order for an unchanged, same-currency cart."""
    if not user.pk or not user.is_active:
        raise OrderCreationError("برای ادامه، حساب کاربری فعال و ذخیره‌شده لازم است.")
    if not isinstance(plan_ids, (list, tuple)) or not plan_ids:
        raise OrderCreationError("سبد خرید خالی است.")
    normalized = list(dict.fromkeys(str(value) for value in plan_ids if value))
    if not normalized:
        raise OrderCreationError("سبد خرید خالی است.")

    try:
        with transaction.atomic():
            from accounts.models import Customer
            locked_user = Customer.objects.select_for_update().filter(pk=user.pk, is_active=True).first()
            if locked_user is None:
                raise OrderCreationError("حساب کاربری فعال پیدا نشد.")
            plans = list(Plan.objects.select_for_update().select_related("product").filter(
                pk__in=normalized, is_active=True, product__is_active=True
            ))
            by_id = {str(plan.pk): plan for plan in plans}
            if len(by_id) != len(normalized):
                raise OrderCreationError("یک یا چند طرح سبد خرید دیگر در دسترس نیست.")
            ordered_plans = [by_id[value] for value in normalized]
            currencies = {plan.currency.upper() for plan in ordered_plans}
            if len(currencies) != 1:
                raise OrderCreationError("برای پرداخت یکجای سبد، همه طرح‌ها باید واحد پول یکسان داشته باشند.")
            currency = next(iter(currencies))
            if currency not in {"IRR", "IRT"}:
                raise OrderCreationError("پرداخت یکجای سبد با زرین‌پال فقط برای ریال یا تومان فعال است.")
            if any(plan.price_minor_units <= 0 for plan in ordered_plans):
                raise OrderCreationError("قیمت یکی از طرح‌های سبد معتبر نیست.")

            candidates = PaymentOrder.objects.filter(
                user=locked_user, status=PaymentOrder.Status.PENDING,
                subscription__isnull=True, items__isnull=False,
            ).distinct().order_by("-created_at")
            total = sum(plan.price_minor_units for plan in ordered_plans)
            for candidate in candidates:
                snapshot = list(candidate.items.select_related("plan").all())
                if len(snapshot) != len(ordered_plans):
                    continue
                same = all(
                    item.plan_id == plan.pk
                    and item.amount_minor_units == plan.price_minor_units
                    and item.currency == plan.currency.upper()
                    for item, plan in zip(snapshot, ordered_plans)
                )
                if same and candidate.currency == currency and candidate.amount_minor_units == total:
                    return candidate

            if total <= 0:
                raise OrderCreationError("مجموع سبد خرید معتبر نیست.")
            order = PaymentOrder.objects.create(
                user=locked_user, plan=ordered_plans[0], subscription=None,
                idempotency_key=uuid.uuid4(), subscription_id_was_explicit=False,
                amount_minor_units=total, currency=currency,
                status=PaymentOrder.Status.PENDING,
            )
            PaymentOrderItem.objects.bulk_create([
                PaymentOrderItem(
                    order=order, plan=plan, product_name=plan.product.name,
                    plan_name=plan.name, amount_minor_units=plan.price_minor_units,
                    currency=plan.currency.upper(), duration_value=plan.duration_value,
                    duration_unit=plan.duration_unit, device_limit=plan.device_limit,
                    position=position,
                )
                for position, plan in enumerate(ordered_plans)
            ])
            return order
    except IntegrityError:
        raise OrderCreationError("ثبت سفارش سبد خرید هم‌زمان با درخواست دیگری انجام شد؛ دوباره تلاش کنید.") from None
