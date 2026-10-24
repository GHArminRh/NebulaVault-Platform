import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models


class CustomerManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("A customer email address is required.")
        email = self.normalize_email(email).strip().lower()
        customer = self.model(email=email, **extra_fields)
        customer.set_password(password)
        customer.save(using=self._db)
        return customer

    def create_superuser(self, email, password=None, **extra_fields):
        raise ValueError("Customers cannot be superusers. Use StaffUser for staff accounts.")


class Customer(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_banned = models.BooleanField(default=False, help_text="Blocked by an administrator; the customer cannot sign in.")
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomerManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        ordering = ["-date_joined"]
        verbose_name = "customer"
        verbose_name_plural = "customers"

    def __str__(self):
        return self.email

    @property
    def is_staff(self):
        return False

    @property
    def is_superuser(self):
        return False

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def has_perm(self, perm, obj=None):
        return False

    def has_module_perms(self, app_label):
        return False


class AccountEmailLog(models.Model):
    """Audit metadata for account verification and password recovery emails."""
    class Purpose(models.TextChoices):
        VERIFICATION = "verification", "Email verification"
        PASSWORD_RESET = "password_reset", "Password recovery"

    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        THROTTLED = "throttled", "Rate limited"
        USED = "used", "Code used"
        EXPIRED = "expired", "Expired"
        SUPERSEDED = "superseded", "Replaced by a newer email"

    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL, related_name="email_history")
    recipient = models.EmailField(db_index=True)
    purpose = models.CharField(max_length=24, choices=Purpose.choices, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SENT, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    code_hash = models.CharField(max_length=64, blank=True, editable=False)
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "account email history"
        verbose_name_plural = "account email history"

    def __str__(self):
        return f"{self.get_purpose_display()} to {self.recipient} ({self.get_status_display()})"
