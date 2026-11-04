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
