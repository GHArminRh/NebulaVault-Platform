import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SEOAuditRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("queued", "Queued"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed")], db_index=True, default="queued", max_length=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("pages_scanned", models.PositiveIntegerField(default=0)),
                ("issues_count", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="seo_audit_runs", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "SEO audit run",
                "verbose_name_plural": "SEO audit runs",
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="SEOAuditIssue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("url", models.URLField(max_length=2048)),
                ("code", models.SlugField(max_length=64)),
                ("severity", models.CharField(choices=[("critical", "Critical"), ("error", "Error"), ("warning", "Warning"), ("info", "Info")], db_index=True, max_length=10)),
                ("title", models.CharField(max_length=200)),
                ("details", models.TextField(blank=True)),
                ("recommendation", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="issues", to="seo.seoauditrun")),
            ],
            options={
                "verbose_name": "SEO audit issue",
                "verbose_name_plural": "SEO audit issues",
                "ordering": ("severity", "url", "code"),
            },
        ),
        migrations.AddConstraint(
            model_name="seoauditissue",
            constraint=models.UniqueConstraint(fields=("run", "url", "code"), name="seo_audit_issue_unique_per_run"),
        ),
        migrations.AddIndex(
            model_name="seoauditissue",
            index=models.Index(fields=["run", "severity"], name="seo_issue_run_severity_idx"),
        ),
    ]
