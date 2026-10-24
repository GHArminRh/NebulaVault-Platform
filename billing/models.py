
import uuid

from django.core.validators import RegexValidator
from django.db import models


currency_code_validator = RegexValidator(
    regex=r"^[A-Z]{3}$",
    message="Use a three-letter uppercase currency code, such as USD.",
)


class PaymentOrder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    """A customer's immutable-at-purchase price snapshot and order."""

    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار"
        PAID = "paid", "پرداخت‌شده"
        CANCELED = "canceled", "لغوشده"
        EXPIRED = "expired", "منقضی‌شده"
        REFUNDED = "refunded", "بازپرداخت‌شده"

    order_number = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    # Identifies retries of the same order-creation request.
    idempotency_key = models.UUIDField(
        null=True,
        blank=True,
        editable=False,
    )
    # Whether the original request explicitly supplied subscription_id.
    # NULL preserves legacy behavior for existing orders.
    subscription_id_was_explicit = models.BooleanField(
        null=True,
        blank=True,
        default=None,
    )
    user = models.ForeignKey(
        "accounts.Customer",
        on_delete=models.PROTECT,
        related_name="payment_orders",
    )

    plan = models.ForeignKey(
        "catalog.Plan",
        on_delete=models.PROTECT,
        related_name="payment_orders",
    )


    # Empty for a new purchase; set when the order renews a subscription.
    subscription = models.ForeignKey(
        "subscriptions.Subscription",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
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
        verbose_name = "سفارش پرداخت"
        verbose_name_plural = "سفارش‌های پرداخت"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_minor_units__gt=0),
                name="billing_order_amount_positive",
            ),
            models.UniqueConstraint(
                fields=["user", "idempotency_key"],
                condition=models.Q(idempotency_key__isnull=False),
                name="billing_order_user_idempotency_unique",
            ),
        ]

    def __str__(self):
        return f"Order {self.order_number} ({self.status})"


class PaymentAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    """A single attempt to pay for an order."""

    class Status(models.TextChoices):
        CREATED = "created", "ایجادشده"
        PENDING = "pending", "در انتظار"
        SUCCEEDED = "succeeded", "موفق"
        FAILED = "failed", "ناموفق"
        CANCELED = "canceled", "لغوشده"
        REFUNDED = "refunded", "بازپرداخت‌شده"

    order = models.ForeignKey(
        PaymentOrder,
        on_delete=models.PROTECT,
        related_name="payment_attempts",
    )

    # Identifies retries of the same client payment request.
    request_key = models.UUIDField(
        null=True,
        blank=True,
        editable=False,
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
        verbose_name = "تلاش پرداخت"
        verbose_name_plural = "تلاش‌های پرداخت"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_minor_units__gt=0),
                name="billing_attempt_amount_positive",
            ),
            models.UniqueConstraint(
                fields=["order", "request_key"],
                condition=models.Q(request_key__isnull=False),
                name="billing_attempt_order_request_unique",
            ),
        ]

    def __str__(self):
        return f"Payment attempt {self.pk} ({self.status})"
