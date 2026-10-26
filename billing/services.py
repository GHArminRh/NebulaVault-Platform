
from uuid import UUID
from copy import copy

from django.db import IntegrityError, transaction
from django.utils import timezone

from catalog.models import Plan
from subscriptions.models import Subscription, SubscriptionRenewal
from subscriptions.services import _add_plan_duration
from licensing.models import License
from licensing.services import issue_license
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import PaymentAttempt, PaymentOrder, PaymentOrderItem


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
    """امکان ایجاد سفارش پرداخت درخواستی وجود ندارد."""


class IdempotencyConflict(OrderCreationError):
    """کلید جلوگیری از ثبت تکراری برای درخواست دیگری استفاده شده است."""


class PaymentAttemptCreationError(Exception):
    """امکان ایجاد تلاش پرداخت درخواستی وجود ندارد."""


class PaymentAttemptIdempotencyConflict(PaymentAttemptCreationError):
    """کلید جلوگیری از ثبت تکراری برای درخواست دیگری استفاده شده است."""


class PaymentFinalizationError(Exception):
    """امکان نهایی‌کردن پرداخت تأییدشده وجود ندارد."""


class PaymentReferenceConflict(PaymentFinalizationError):
    """شناسه پرداخت ارائه‌دهنده به‌صورت ناسازگار دوباره استفاده شده است."""


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
            "شناسه معتبر پرداخت از طرف ارائه‌دهنده الزامی است."
        )

    provider_reference = provider_reference.strip()
    if not provider_reference or len(provider_reference) > 255:
        raise PaymentFinalizationError(
            "شناسه معتبر پرداخت از طرف ارائه‌دهنده الزامی است."
        )

    if (
        isinstance(confirmed_amount_minor_units, bool)
        or not isinstance(confirmed_amount_minor_units, int)
        or confirmed_amount_minor_units <= 0
    ):
        raise PaymentFinalizationError("مبلغ تأییدشده معتبر نیست.")

    if not isinstance(confirmed_currency, str):
        raise PaymentFinalizationError("واحد پول تأییدشده معتبر نیست.")

    confirmed_currency = confirmed_currency.strip().upper()
    if (
        len(confirmed_currency) != 3
        or not confirmed_currency.isascii()
        or not confirmed_currency.isalpha()
    ):
        raise PaymentFinalizationError("واحد پول تأییدشده معتبر نیست.")

    try:
        attempt_pk = UUID(str(attempt_id))
    except (TypeError, ValueError, AttributeError):
        raise PaymentFinalizationError(
            "تلاش پرداخت معتبر الزامی است."
        ) from None

    order_id = (
        PaymentAttempt.objects
        .filter(pk=attempt_pk)
        .values_list("order_id", flat=True)
        .first()
    )

    if order_id is None:
        raise PaymentFinalizationError(
            "تلاش پرداخت پیدا نشد."
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
                    "این پرداخت قبلاً با جزئیات متفاوت نهایی شده است."
                )

            if attempt.status not in {
                PaymentAttempt.Status.CREATED,
                PaymentAttempt.Status.PENDING,
            }:
                raise PaymentFinalizationError(
                    "این تلاش پرداخت قابل نهایی‌کردن نیست."
                )

            if order.status != PaymentOrder.Status.PENDING:
                raise PaymentFinalizationError(
                    "فقط سفارش‌های در انتظار قابل نهایی‌کردن هستند."
                )

            if (
                attempt.amount_minor_units != order.amount_minor_units
                or attempt.currency != order.currency
            ):
                raise PaymentFinalizationError(
                    "تلاش پرداخت با سفارش مربوط به آن مطابقت ندارد."
                )

            if (
                confirmed_amount_minor_units != order.amount_minor_units
                or confirmed_currency != order.currency
            ):
                raise PaymentFinalizationError(
                    "پرداخت تأییدشده با سفارش مطابقت ندارد."
                )

            if attempt.provider_reference not in (None, provider_reference):
                raise PaymentReferenceConflict(
                    "این تلاش پرداخت از قبل شناسه دیگری از ارائه‌دهنده دارد."
                )

            cart_items = list(order.items.select_related("plan__product").all())
            if cart_items:
                if (
                    sum(item.amount_minor_units for item in cart_items) != order.amount_minor_units
                    or any(item.currency != order.currency for item in cart_items)
                ):
                    raise PaymentFinalizationError("اقلام ثبت‌شده با مبلغ و واحد پول سفارش مطابقت ندارند.")
                now = timezone.now()
                issued_keys = []
                for line in cart_items:
                    plan_item = line.plan
                    duration_plan = copy(plan_item)
                    duration_plan.duration_value = line.duration_value
                    duration_plan.duration_unit = line.duration_unit
                    subscription = Subscription.objects.create(
                        user=order.user, product=plan_item.product,
                        kind=Subscription.Kind.PAID, status=Subscription.Status.ACTIVE,
                        plan=plan_item, trial_redemption=None, starts_at=now,
                        expires_at=_add_plan_duration(now, duration_plan),
                    )
                    license_record, license_key = issue_license(subscription)
                    issued_keys.append({
                        "product_name": line.product_name,
                        "plan_name": line.plan_name,
                        "license_key": license_key,
                    })
                attempt.status = PaymentAttempt.Status.SUCCEEDED
                attempt.provider_reference = provider_reference
                attempt.confirmed_at = now
                attempt.save(update_fields=["status", "provider_reference", "confirmed_at", "updated_at"])
                order.status = PaymentOrder.Status.PAID
                order.paid_at = now
                order.save(update_fields=["status", "paid_at", "updated_at"])
                attempt.issued_license_keys = issued_keys
                attempt.issued_license_key = issued_keys[0]["license_key"] if issued_keys else None
                for item_data in issued_keys:
                    recipient = (order.user.email or "").strip()
                    if recipient:
                        product_name = item_data["product_name"]
                        plan_name = item_data["plan_name"]
                        key = item_data["license_key"]
                        body = (
                            f"سلام {order.user.username} عزیز،\\n\\n"
                            f"پرداخت طرح «{plan_name}» برای محصول «{product_name}» "
                            "با موفقیت تأیید شد و لایسنس شما صادر شد.\\n\\n"
                            f"کلید لایسنس: {key}\\n\\nاین کلید را در اختیار دیگران قرار ندهید."
                        )
                        transaction.on_commit(
                            lambda to=recipient, subject_product=product_name, plain=body: send_mail(
                                subject=f"لایسنس محصول {subject_product} صادر شد | نبیولا والت",
                                message=plain, from_email=None, recipient_list=[to],
                                fail_silently=True,
                            )
                        )
                return attempt

            now = timezone.now()
            plan = order.plan
            issued_license_key = None
            issued_license_record = None

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
                        "این اشتراک متعلق به این مشتری نیست."
                    )

                if subscription.kind != Subscription.Kind.PAID:
                    raise PaymentFinalizationError(
                        "اشتراک آزمایشی قابل تمدید نیست."
                    )

                if subscription.status == Subscription.Status.CANCELED:
                    raise PaymentFinalizationError(
                        "اشتراک لغوشده قابل تمدید نیست."
                    )

                if (
                    subscription.plan_id != plan.pk
                    or subscription.product_id != plan.product_id
                ):
                    raise PaymentFinalizationError(
                        "طرح سفارش با اشتراک مطابقت ندارد."
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

            # Every successfully paid subscription must have a license.
            # Keep the raw key out of the database; expose it only for delivery.
            existing_license = License.objects.filter(subscription=subscription).first()
            if existing_license is None:
                issued_license_record, issued_license_key = issue_license(subscription)
            else:
                issued_license_record = existing_license

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

            if issued_license_key:
                # The caller may display this key once (e.g. immediately after checkout).
                attempt.issued_license_key = issued_license_key

                # Also deliver the key by email for gateway callbacks that have no
                # browser session. Email failure must not undo a verified payment.
                recipient = (subscription.user.email or "").strip()
                if recipient:
                    email_context = {
                        "user": subscription.user,
                        "subscription": subscription,
                        "license": issued_license_record,
                        "license_key": issued_license_key,
                    }
                    html_body = render_to_string(
                        "registration/license_issued_email.html", email_context
                    )
                    text_body = (
                        f"سلام {subscription.user.username} عزیز،\n\n"
                        f"پرداخت طرح «{plan.name}» برای محصول «{plan.product.name}» "
                        "با موفقیت تأیید شد و لایسنس شما صادر شد.\n\n"
                        f"کلید لایسنس: {issued_license_key}\n\n"
                        "مدت اعتبار از اولین فعال‌سازی موفق لایسنس در برنامه دسکتاپ آغاز می‌شود؛ "
                        "تاریخ انقضا پس از فعال‌سازی محاسبه خواهد شد.\n\n"
                        "این کلید را در اختیار دیگران قرار ندهید. "
                        "این پیام به‌صورت خودکار از طرف نبیولا والت ارسال شده است."
                    )
                    transaction.on_commit(
                        lambda to=recipient, subject_product=plan.product.name,
                        plain=text_body, html=html_body: send_mail(
                            subject=f"لایسنس محصول {subject_product} صادر شد | نبیولا والت",
                            message=plain,
                            from_email=None,
                            recipient_list=[to],
                            html_message=html,
                            fail_silently=True,
                        )
                    )

            return attempt

    except PaymentAttempt.DoesNotExist:
        raise PaymentFinalizationError(
            "تلاش پرداخت پیدا نشد."
        ) from None
    except PaymentOrder.DoesNotExist:
        raise PaymentFinalizationError(
            "سفارش پرداخت پیدا نشد."
        ) from None
    except Subscription.DoesNotExist:
        raise PaymentFinalizationError(
            "اشتراک پیدا نشد."
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
                "این شناسه ارائه‌دهنده قبلاً استفاده شده است."
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
                "این شناسه ارائه‌دهنده قبلاً استفاده شده است."
            ) from None

        # The unique violation was not attributable to an existing reference.
        raise
