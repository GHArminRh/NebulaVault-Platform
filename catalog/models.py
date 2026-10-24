import uuid


import hashlib

from django.core.validators import RegexValidator
from django.db import models
from django.utils.text import slugify

from .rich_text import clean_rich_text


currency_code_validator = RegexValidator(
    regex=r"^[A-Z]{3}$",
    message="Enter a three-letter uppercase currency code, such as USD.",
)

sha256_validator = RegexValidator(
    regex=r"^[0-9a-fA-F]{64}$",
    message="SHA-256 must contain exactly 64 hexadecimal characters.",
)


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    """The software product itself; downloading it is free."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    website_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "software product"
        verbose_name_plural = "software products"

    def save(self, *args, **kwargs):
        base_slug = slugify(self.name) or "product"
        candidate = base_slug[: self._meta.get_field("slug").max_length]
        suffix = 2
        queryset = type(self).objects.all()
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)
        while queryset.filter(slug=candidate).exists():
            ending = f"-{suffix}"
            candidate = f"{base_slug[: self._meta.get_field('slug').max_length - len(ending)]}{ending}"
            suffix += 1
        self.slug = candidate
        self.description = clean_rich_text(self.description)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Release(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    """A freely downloadable published version of a product."""

    class Platform(models.TextChoices):
        WINDOWS = "windows", "Windows"
        MACOS = "macos", "macOS"
        LINUX = "linux", "Linux"

    class Architecture(models.TextChoices):
        X64 = "x64", "x64"
        ARM64 = "arm64", "ARM64"
        UNIVERSAL = "universal", "All architectures"

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="releases",
    )
    version = models.CharField(max_length=40)
    platform = models.CharField(
        max_length=10,
        choices=Platform.choices,
    )
    architecture = models.CharField(
        max_length=10,
        choices=Architecture.choices,
    )

    installer_file = models.FileField(upload_to="releases/%Y/%m/", blank=True, help_text="Upload the release file; SHA-256 is calculated automatically.")
    download_url = models.URLField(max_length=1000, blank=True)
    sha256 = models.CharField(max_length=64, validators=[sha256_validator], blank=True, editable=False)
    release_notes = models.TextField(blank=True)

    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_at", "version"]
        verbose_name = "software release"
        verbose_name_plural = "software releases"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "product",
                    "version",
                    "platform",
                    "architecture",
                ],
                name="catalog_release_unique_build",
            ),
        ]

    def save(self, *args, **kwargs):
        uploaded_file = self.installer_file
        if uploaded_file:
            digest = hashlib.sha256()

            # A new upload still lives in Django's temporary upload handler.
            # Read that object directly; FieldFile.open() tries to find it in
            # permanent storage before it has been saved there.
            if uploaded_file._committed:
                with uploaded_file.storage.open(uploaded_file.name, "rb") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(chunk)
            else:
                source = uploaded_file.file
                try:
                    source.seek(0)
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(chunk)
                finally:
                    source.seek(0)
            self.sha256 = digest.hexdigest()
        else:
            self.sha256 = ""

        self.release_notes = clean_rich_text(self.release_notes)
        super().save(*args, **kwargs)

        # Now the upload is in permanent storage, so its URL is safe to use.
        if self.installer_file and not self.download_url:
            self.download_url = self.installer_file.url
            type(self).objects.filter(pk=self.pk).update(download_url=self.download_url)

    def __str__(self):
        return (
            f"{self.product.name} {self.version} "
            f"({self.platform}/{self.architecture})"
        )


class Plan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    """A paid subscription offer for a software product."""

    class DurationUnit(models.TextChoices):
        DAYS = "days", "Days"
        MONTHS = "months", "Months"
        YEARS = "years", "Years"

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="plans",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)

    duration_unit = models.CharField(
        max_length=10,
        choices=DurationUnit.choices,
        default=DurationUnit.MONTHS,
    )
    duration_value = models.PositiveSmallIntegerField(default=1)

    # Amount in the currency's minor unit.
    # Example: USD 1999 means $19.99.
    price_minor_units = models.PositiveBigIntegerField()
    currency = models.CharField(
        max_length=3,
        default="USD",
        validators=[currency_code_validator],
    )

    device_limit = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "price_minor_units", "name"]
        verbose_name = "subscription plan"
        verbose_name_plural = "subscription plans"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "slug"],
                name="catalog_plan_unique_slug_per_product",
            ),
            models.CheckConstraint(
                condition=models.Q(duration_value__gte=1),
                name="catalog_plan_duration_at_least_one",
            ),
            models.CheckConstraint(
                condition=models.Q(device_limit__gte=1),
                name="catalog_plan_device_limit_at_least_one",
            ),
            models.CheckConstraint(
                condition=models.Q(price_minor_units__gt=0),
                name="catalog_plan_price_must_be_positive",
            ),
        ]

    def save(self, *args, **kwargs):
        base_slug = slugify(self.name) or "plan"
        max_length = self._meta.get_field("slug").max_length
        candidate = base_slug[:max_length]
        suffix = 2
        queryset = type(self).objects.filter(product_id=self.product_id)
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)
        while queryset.filter(slug=candidate).exists():
            ending = f"-{suffix}"
            candidate = f"{base_slug[: max_length - len(ending)]}{ending}"
            suffix += 1
        self.slug = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} — {self.name}"
