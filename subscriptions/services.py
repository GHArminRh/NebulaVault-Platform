
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Subscription, TrialRedemption


TRIAL_DAYS = 7


class TrialAlreadyUsed(Exception):
    """The customer has already redeemed the trial for this product."""


class TrialUnavailable(Exception):
    """The trial cannot be started for this customer or product."""


def start_trial(*, user, product):
    """
    Atomically create a customer's one-time trial record
    and its corresponding subscription.

    Returns the created Subscription.
    """

    if not user.pk or not user.is_active:
        raise TrialUnavailable("An active, saved user account is required.")

    if not product.pk or not product.is_active:
        raise TrialUnavailable("This product is not available for trial.")

    try:
        with transaction.atomic():
            already_used = TrialRedemption.objects.filter(
                user=user,
                product=product,
            ).exists()

            if already_used:
                raise TrialAlreadyUsed(
                    "The trial has already been used for this product."
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
                "The trial has already been used for this product."
            ) from None

        # Do not hide unrelated database integrity errors.
        raise
