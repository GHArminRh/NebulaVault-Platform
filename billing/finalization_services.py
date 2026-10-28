"""Finalize payments only after trusted provider-side verification."""

from copy import copy
from uuid import UUID

from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string
from django.utils import timezone

from subscriptions.models import Subscription, SubscriptionRenewal
from subscriptions.services import _add_plan_duration
from licensing.models import License
from licensing.services import issue_license

from .models import PaymentAttempt, PaymentOrder
from .services import (
    PaymentFinalizationError,
    PaymentReferenceConflict,
    _is_provider_reference_integrity_error,
)


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

                    # If this exact product/plan already has an active license,
                    # treat the cart line as a renewal instead of issuing a
                    # second independent license.
                    existing_subscriptions = list(
                        Subscription.objects.select_for_update()
                        .filter(
                            user=order.user,
                            product=plan_item.product,
                            plan=plan_item,
                            kind=Subscription.Kind.PAID,
                            license__status=License.Status.ACTIVE,
                        )
                        .exclude(status=Subscription.Status.CANCELED)
                        .order_by("created_at")[:2]
                    )
                    if len(existing_subscriptions) > 1:
                        raise PaymentFinalizationError(
                            "برای این طرح بیش از یک لایسنس پیدا شد؛ تمدید خودکار ممکن نیست."
                        )

                    if existing_subscriptions:
                        subscription = existing_subscriptions[0]
                        previous_expiry = subscription.expires_at
                        extension_start = max(previous_expiry, now)
                        new_expiry = _add_plan_duration(extension_start, duration_plan)
                        # Renewal references are unique per order line because
                        # one cart payment may renew multiple subscriptions.
                        renewal_reference = f"{provider_reference[:180]}:cart-item:{line.pk}"
                        SubscriptionRenewal.objects.create(
                            subscription=subscription,
                            payment_reference=renewal_reference,
                            previous_expires_at=previous_expiry,
                            new_expires_at=new_expiry,
                            amount_minor_units=line.amount_minor_units,
                            currency=line.currency,
                        )
                        subscription.expires_at = new_expiry
                        subscription.status = Subscription.Status.ACTIVE
                        subscription.save(
                            update_fields=["expires_at", "status", "updated_at"]
                        )
                    else:
                        subscription = Subscription.objects.create(
                            user=order.user, product=plan_item.product,
                            kind=Subscription.Kind.PAID, status=Subscription.Status.ACTIVE,
                            plan=plan_item, trial_redemption=None, starts_at=now,
                            expires_at=_add_plan_duration(now, duration_plan),
                        )

                    # Existing active licenses keep their current key. Only
                    # first purchases issue and deliver a new key.
                    existing_license = License.objects.filter(
                        subscription=subscription
                    ).first()
                    if existing_license is None:
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
                            f"سلام {order.user.username} عزیز،\n\n"
                            f"پرداخت طرح «{plan_name}» برای محصول «{product_name}» "
                            "با موفقیت تأیید شد و لایسنس شما صادر شد.\n\n"
                            f"کلید لایسنس: {key}\n\nاین کلید را در اختیار دیگران قرار ندهید."
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
