import uuid

from django.db import models

from accounts.models import Customer


class CustomerAPIToken(models.Model):
    """Revocable, expiring API credential; the raw token is never stored."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="api_tokens",
    )
    token_prefix = models.CharField(max_length=12, db_index=True)
    token_digest = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "customer API token"
        verbose_name_plural = "customer API tokens"
        indexes = [
            models.Index(fields=("customer", "revoked_at"), name="api_cust_revoke_idx"),
        ]

    @property
    def is_revoked(self):
        return self.revoked_at is not None

    def __str__(self):
        return f"{self.customer_id} · {self.token_prefix}"
