import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class License(models.Model):
    """A license entitlement tied to one subscription; plaintext keys are never stored."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        REVOKED = "revoked", "Revoked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.OneToOneField(
        "subscriptions.Subscription",
        on_delete=models.PROTECT,
        related_name="license",
    )
    key_prefix = models.CharField(max_length=16, blank=True, editable=False, db_index=True)
    key_digest = models.CharField(max_length=64, unique=True, editable=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_validated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Application license"
        verbose_name_plural = "Application licenses"

    def save(self, *args, **kwargs):
        if not self.key_digest or len(self.key_digest) != 64:
            raise ValidationError("A license must be issued with a key digest.")
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.subscription_id and self.subscription.plan_id:
            if self.subscription.product_id != self.subscription.plan.product_id:
                raise ValidationError({"subscription": "The subscription product does not match its plan."})

    @property
    def is_entitled(self):
        subscription = self.subscription
        return (
            self.status == self.Status.ACTIVE
            and subscription.user.is_active
            and subscription.product.is_active
            and subscription.is_currently_valid
        )

    @property
    def display_key(self):
        # Import lazily to avoid a model/service import cycle.
        from .services import get_stored_license_key
        return get_stored_license_key(self)

    @property
    def activation_limit(self):
        return self.subscription.plan.device_limit if self.subscription.plan_id else 1

    @property
    def active_activation_count(self):
        return self.activations.filter(is_active=True).count()

    def __str__(self):
        # Do not expose even the identifying prefix in admin relations or dropdowns.
        return f"License for {self.subscription.user}"


class LicenseActivation(models.Model):
    """One licensed device; raw device fingerprints are never persisted."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license = models.ForeignKey(License, on_delete=models.PROTECT, related_name="activations")
    fingerprint_digest = models.CharField(max_length=64)
    device_label = models.CharField(max_length=120, blank=True)
    app_version = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    first_activated_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_seen_at"]
        verbose_name = "License activation"
        verbose_name_plural = "License activations"
        constraints = [
            models.UniqueConstraint(fields=("license", "fingerprint_digest"), name="licensing_unique_device_per_license"),
        ]

    def __str__(self):
        return f"{self.device_label or 'Device'} — {self.license.key_prefix}"
