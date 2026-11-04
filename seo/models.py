from django.conf import settings
from django.db import models


class SEOAuditRun(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.QUEUED,
        db_index=True,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seo_audit_runs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    pages_scanned = models.PositiveIntegerField(default=0)
    issues_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "SEO audit run"
        verbose_name_plural = "SEO audit runs"

    def __str__(self):
        return f"SEO audit #{self.pk} — {self.get_status_display()}"


class SEOAuditIssue(models.Model):
    class Severity(models.TextChoices):
        CRITICAL = "critical", "Critical"
        ERROR = "error", "Error"
        WARNING = "warning", "Warning"
        INFO = "info", "Info"

    run = models.ForeignKey(
        SEOAuditRun,
        on_delete=models.CASCADE,
        related_name="issues",
    )
    url = models.URLField(max_length=2048)
    code = models.SlugField(max_length=64)
    severity = models.CharField(max_length=10, choices=Severity.choices, db_index=True)
    title = models.CharField(max_length=200)
    details = models.TextField(blank=True)
    recommendation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("severity", "url", "code")
        verbose_name = "SEO audit issue"
        verbose_name_plural = "SEO audit issues"
        constraints = [
            models.UniqueConstraint(
                fields=("run", "url", "code"),
                name="seo_audit_issue_unique_per_run",
            )
        ]
        indexes = [
            models.Index(fields=("run", "severity"), name="seo_issue_run_severity_idx"),
        ]

    def __str__(self):
        return f"{self.get_severity_display()}: {self.title}"


class SearchConsoleConnection(models.Model):
    site_url = models.CharField(max_length=255, unique=True)
    connected_email = models.EmailField(blank=True)
    refresh_token_encrypted = models.TextField()
    granted_scope = models.TextField(blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_sync_error = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Search Console connection"
        verbose_name_plural = "Search Console connections"

    def __str__(self):
        return self.site_url


class SearchConsoleMetric(models.Model):
    class DimensionType(models.TextChoices):
        DAILY = "daily", "Daily"
        QUERY = "query", "Query"
        PAGE = "page", "Page"

    connection = models.ForeignKey(
        SearchConsoleConnection,
        on_delete=models.CASCADE,
        related_name="metrics",
    )
    date = models.DateField(db_index=True)
    dimension_type = models.CharField(max_length=8, choices=DimensionType.choices)
    dimension_value = models.CharField(max_length=2048, blank=True)
    clicks = models.FloatField(default=0)
    impressions = models.FloatField(default=0)
    ctr = models.FloatField(default=0)
    position = models.FloatField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("date", "dimension_type", "dimension_value")
        constraints = [
            models.UniqueConstraint(
                fields=("connection", "date", "dimension_type", "dimension_value"),
                name="seo_gsc_metric_unique",
            )
        ]
        indexes = [
            models.Index(
                fields=("connection", "dimension_type", "date"),
                name="seo_gsc_type_date_idx",
            )
        ]

    def __str__(self):
        return f"{self.date} — {self.dimension_type}: {self.dimension_value}"
