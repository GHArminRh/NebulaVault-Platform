import calendar

from django.db import IntegrityError, transaction
from datetime import timedelta
from django.utils import timezone
from .models import Subscription, SubscriptionRenewal, TrialRedemption


TRIAL_DAYS = 7


class TrialAlreadyUsed(Exception):
    """این مشتری قبلاً از دوره آزمایشی این محصول استفاده کرده است."""


class TrialUnavailable(Exception):
    """امکان شروع دوره آزمایشی برای این مشتری یا محصول وجود ندارد."""


def start_trial(*, user, product):
    """
    Atomically create a customer's one-time trial record
    and its corresponding subscription.

    Returns the created Subscription.
    """

    if not user.pk or not user.is_active:
        raise TrialUnavailable("برای ادامه، حساب کاربری فعال و ذخیره‌شده لازم است.")

    if not product.pk or not product.is_active:
        raise TrialUnavailable("این محصول دوره آزمایشی ندارد.")

    try:
        with transaction.atomic():
            already_used = TrialRedemption.objects.filter(
                user=user,
                product=product,
            ).exists()

            if already_used:
                raise TrialAlreadyUsed(
                    "دوره آزمایشی این محصول قبلاً استفاده شده است."
                )

            starts_at = timezone.now()
            expires_at = starts_at + timedelta(days=TRIAL_DAYS)

            redemption = TrialRedemption.objects.create(
                user=user,
                product=product,
                started_at=starts_at,
                ends_at=expires_at,
            )

            subscription = Subscription.objects.create(
                user=user,
                product=product,
                kind=Subscription.Kind.TRIAL,
                status=Subscription.Status.TRIALING,
                plan=None,
                trial_redemption=redemption,
                starts_at=starts_at,
                expires_at=expires_at,
            )

            return subscription

    except IntegrityError:
        # A concurrent request may have created the unique trial record.
        if TrialRedemption.objects.filter(
            user=user,
            product=product,
        ).exists():
            raise TrialAlreadyUsed(
                "دوره آزمایشی این محصول قبلاً استفاده شده است."
            ) from None

        # Do not hide unrelated database integrity errors.
        raise










class RenewalNotAllowed(Exception):
    """این اشتراک واجد شرایط تمدید نیست."""


class PaymentReferenceConflict(Exception):
    """شناسه پرداخت با جزئیات متفاوت دوباره استفاده شده است."""


def _add_plan_duration(start, plan):
    """Add a plan's calendar-based duration to an aware datetime."""

    if plan.duration_unit == "days":
        from datetime import timedelta

        return start + timedelta(days=plan.duration_value)

    if plan.duration_unit not in {"months", "years"}:
        raise RenewalNotAllowed("مدت اشتراک پشتیبانی نمی‌شود.")

    months_to_add = plan.duration_value

    if plan.duration_unit == "years":
        months_to_add *= 12

    month_index = start.month - 1 + months_to_add
    year = start.year + month_index // 12
    month = month_index % 12 + 1

    day = min(start.day, calendar.monthrange(year, month)[1])

    return start.replace(year=year, month=month, day=day)


def renew_subscription(
    *,
    subscription_id,
    payment_reference,
    confirmed_amount_minor_units,
    confirmed_currency,
):
    """
    Record a renewal after trusted server-side payment verification.

    IMPORTANT:
    Only a trusted payment-processing service may call this function.
    The arguments must come from verified server-side payment data,
    never directly from a browser request.
    """

    if not payment_reference or not payment_reference.strip():
        raise RenewalNotAllowed("شناسه پرداخت الزامی است.")

    if confirmed_amount_minor_units <= 0:
        raise RenewalNotAllowed("مبلغ پرداخت تأییدشده معتبر نیست.")

    if not confirmed_currency:
        raise RenewalNotAllowed("واحد پول تأییدشده الزامی است.")

    try:
        with transaction.atomic():
            subscription = (
                Subscription.objects
                .select_for_update(of=("self",))
                .select_related("plan", "product")
                .get(pk=subscription_id)
            )

            # Idempotency: a previously processed payment must not
            # extend the subscription a second time.
            existing = SubscriptionRenewal.objects.filter(
                payment_reference=payment_reference,
            ).first()

            if existing:
                if (
                    existing.subscription_id == subscription.pk
                    and existing.amount_minor_units
                    == confirmed_amount_minor_units
                    and existing.currency == confirmed_currency
                ):
                    return existing

                raise PaymentReferenceConflict(
                    "این شناسه پرداخت قبلاً استفاده شده است."
                )

            if subscription.kind != Subscription.Kind.PAID:
                raise RenewalNotAllowed(
                    "تمدید پولی برای اشتراک آزمایشی امکان‌پذیر نیست."
                )

            if subscription.status == Subscription.Status.CANCELED:
                raise RenewalNotAllowed(
                    "اشتراک لغوشده قابل تمدید نیست."
                )

            plan = subscription.plan

            if plan is None:
                raise RenewalNotAllowed(
                    "اشتراک پولی باید طرح داشته باشد."
                )

            if confirmed_amount_minor_units != plan.price_minor_units:
                raise RenewalNotAllowed(
                    "مبلغ تأییدشده با قیمت طرح مطابقت ندارد."
                )

            if confirmed_currency != plan.currency:
                raise RenewalNotAllowed(
                    "واحد پول تأییدشده با طرح مطابقت ندارد."
                )

            now = timezone.now()
            previous_expiry = subscription.expires_at

            # Preserve remaining time for early renewals.
            # If already expired, start the new period from now.
            extension_start = max(previous_expiry, now)
            new_expiry = _add_plan_duration(extension_start, plan)

            renewal = SubscriptionRenewal.objects.create(
                subscription=subscription,
                payment_reference=payment_reference,
                previous_expires_at=previous_expiry,
                new_expires_at=new_expiry,
                amount_minor_units=confirmed_amount_minor_units,
                currency=confirmed_currency,
            )

            subscription.expires_at = new_expiry
            subscription.status = Subscription.Status.ACTIVE
            subscription.save(
                update_fields=[
                    "expires_at",
                    "status",
                    "updated_at",
                ]
            )

            return renewal

    except IntegrityError:
        # A concurrent request may have processed this payment first.
        existing = SubscriptionRenewal.objects.filter(
            payment_reference=payment_reference,
        ).first()

        if existing:
            if (
                existing.subscription_id == subscription_id
                and existing.amount_minor_units
                == confirmed_amount_minor_units
                and existing.currency == confirmed_currency
            ):
                return existing

            raise PaymentReferenceConflict(
                "این شناسه پرداخت قبلاً استفاده شده است."
            ) from None

        raise
