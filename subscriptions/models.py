import uuid


from datetime import timedelta

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


TRIAL_DURATION = timedelta(days=7)


class TrialRedemption(models.Model):
    """
    Permanent record that a customer used the trial for a product.
    This record must not be deleted when the trial expires.
    """

    user = models.ForeignKey(
        "accounts.Customer",
        on_delete=models.PROTECT,
        related_name="trial_redemptions",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="trial_redemptions",
    )

    started_at = models.DateTimeField()
    ends_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "trial redemption"
        verbose_name_plural = "trial redemptions"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"],
                name="subscriptions_unique_trial_per_user_product",
            ),
            models.CheckConstraint(
                condition=Q(ends_at__gt=models.F("started_at")),
                name="subscriptions_trial_end_after_start",
            ),
        ]

    def clean(self):
        super().clean()

        if self.started_at and self.ends_at:
            if self.ends_at <= self.started_at:
                raise ValidationError(
                    {"ends_at": "The trial end date must be after its start date."}
                )

            if self.ends_at - self.started_at > TRIAL_DURATION:
                raise ValidationError(
                    {"ends_at": "A trial cannot last longer than 7 days."}
                )

    def __str__(self):
        return f"{self.user} — {self.product} trial"


class Subscription(models.Model):
    """A customer's trial or paid subscription."""

    class Kind(models.TextChoices):
        TRIAL = "trial", "Trial"
        PAID = "paid", "Paid"

    class Status(models.TextChoices):
        TRIALING = "trialing", "Trial active"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        EXPIRED = "expired", "Expired"
        CANCELED = "canceled", "Canceled"

    user = models.ForeignKey(
        "accounts.Customer",
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )

    kind = models.CharField(
        max_length=10,
        choices=Kind.choices,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
    )

    # Trial subscriptions do not require a paid plan.
    plan = models.ForeignKey(
        "catalog.Plan",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="subscriptions",
    )

    # Present only for a trial subscription.
    trial_redemption = models.OneToOneField(
        TrialRedemption,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="subscription",
    )

    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "subscription"
        verbose_name_plural = "subscriptions"
        constraints = [
            models.CheckConstraint(
                condition=Q(expires_at__gt=models.F("starts_at")),
                name="subscriptions_end_after_start",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        kind="trial",
                        plan__isnull=True,
                        trial_redemption__isnull=False,
                    )
                    | Q(
                        kind="paid",
                        plan__isnull=False,
                        trial_redemption__isnull=True,
                    )
                ),
                name="subscriptions_kind_matches_plan_and_trial",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}

        if self.starts_at and self.expires_at:
            if self.expires_at <= self.starts_at:
                errors["expires_at"] = (
                    "The subscription end date must be after its start date."
                )

        if self.plan_id and self.product_id:
            if self.plan.product_id != self.product_id:
                errors["plan"] = (
                    "The selected plan must belong to the selected product."
                )

        if self.kind == self.Kind.TRIAL:
            if self.status not in {
                self.Status.TRIALING,
                self.Status.EXPIRED,
                self.Status.CANCELED,
            }:
                errors["status"] = (
                    "A trial must have Trial active, Expired, or Canceled status."
                )

            if self.trial_redemption_id:
                redemption = self.trial_redemption

                if self.user_id and redemption.user_id != self.user_id:
                    errors["trial_redemption"] = (
                        "The trial record must belong to this customer."
                    )
                elif (
                    self.product_id
                    and redemption.product_id != self.product_id
                ):
                    errors["trial_redemption"] = (
                        "The trial record must belong to this product."
                    )

                if (
                    self.starts_at
                    and self.expires_at
                    and self.expires_at - self.starts_at > TRIAL_DURATION
                ):
                    errors["expires_at"] = (
                        "A trial subscription cannot exceed 7 days."
                    )

        elif self.kind == self.Kind.PAID:
            if self.status == self.Status.TRIALING:
                errors["status"] = (
                    "A paid subscription cannot have Trial active status."
                )

        if errors:
            raise ValidationError(errors)

    @property
    def has_been_activated(self):
        """Whether a paid subscription has ever been activated on a device."""
        if self.kind != self.Kind.PAID or not self.pk:
            return True

        try:
            license_record = self.license
        except ObjectDoesNotExist:
            # A manually-created subscription may not have a license yet.
            return False

        return license_record.activations.exists()

    @property
    def is_waiting_for_activation(self):
        """Whether a paid, active subscription is waiting for its first activation."""
        return (
            self.kind == self.Kind.PAID
            and self.status == self.Status.ACTIVE
            and not self.has_been_activated
        )

    @property
    def is_currently_valid(self):
        """Whether this subscription is within its validity period."""
        now = timezone.now()

        return (
            self.status
            in {
                self.Status.TRIALING,
                self.Status.ACTIVE,
            }
            and self.starts_at <= now < self.expires_at
        )

    def __str__(self):
        return f"{self.user} — {self.product} ({self.kind})"





class SubscriptionRenewal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    """Audit record for a successfully processed paid renewal."""

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.PROTECT,
        related_name="renewals",
    )

    # Must be supplied by trusted server-side payment processing.
    payment_reference = models.CharField(
        max_length=255,
        unique=True,
    )

    previous_expires_at = models.DateTimeField()
    new_expires_at = models.DateTimeField()

    amount_minor_units = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=3)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Subscription renewal"
        verbose_name_plural = "Subscription renewals"
        constraints = [
            models.CheckConstraint(
                condition=Q(new_expires_at__gt=models.F("previous_expires_at")),
                name="subscriptions_renewal_end_after_previous",
            ),
            models.CheckConstraint(
                condition=Q(amount_minor_units__gt=0),
                name="subscriptions_renewal_amount_positive",
            ),
        ]

    def __str__(self):
        return (
            f"Renewal for subscription {self.subscription_id} "
            f"({self.payment_reference})"
        )
