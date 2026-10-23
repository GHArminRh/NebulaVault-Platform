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
        raise ValueError("Customers cannot be superusers. Use Django's built-in User for staff.")


class Customer(AbstractBaseUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
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
