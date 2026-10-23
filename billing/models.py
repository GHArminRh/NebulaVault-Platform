
import uuid

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


currency_code_validator = RegexValidator(
    regex=r"^[A-Z]{3}$",
    message="Use a three-letter uppercase currency code, such as USD.",
)


class PaymentOrder(models.Model):
    """A customer's immutable-at-purchase price snapshot and order."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        CANCELED = "canceled", "Canceled"
        EXPIRED = "expired", "Expired"
        REFUNDED = "refunded", "Refunded"

    order_number = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payment_orders",
    )

    plan = models.ForeignKey(
        "catalog.Plan",
        on_delete=models.PROTECT,
        related_name="payment_orders",
    )

    # Price snapshot: later plan price changes must not rewrite this order.
    amount_minor_units = models.PositiveBigIntegerField()
    currency = models.CharField(
        max_length=3,
        validators=[currency_code_validator],
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Payment order"
        verbose_name_plural = "Payment orders"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_minor_units__gt=0),
                name="billing_order_amount_positive",
            ),
        ]

    def __str__(self):
        return f"Order {self.order_number} ({self.status})"


class PaymentAttempt(models.Model):
    """A single attempt to pay for an order."""

    class Status(models.TextChoices):
        CREATED = "created", "Created"
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"
        REFUNDED = "refunded", "Refunded"

    order = models.ForeignKey(
        PaymentOrder,
        on_delete=models.PROTECT,
        related_name="payment_attempts",
    )

    # Examples: a provider identifier or an internal manual-payment channel.
    # No specific provider is required by this model.
    provider = models.CharField(max_length=40)

    # Set only when a provider supplies a reference.
    # A provider reference can belong to at most one attempt.
    provider_reference = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )

    # Unique key for identifying retries of the same payment request.
    idempotency_key = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    # Snapshot of the amount requested for this particular attempt.
    amount_minor_units = models.PositiveBigIntegerField()
    currency = models.CharField(
        max_length=3,
        validators=[currency_code_validator],
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.CREATED,
    )

    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Payment attempt"
        verbose_name_plural = "Payment attempts"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_minor_units__gt=0),
                name="billing_attempt_amount_positive",
            ),
        ]

    def __str__(self):
        return f"Payment attempt {self.pk} ({self.status})"
