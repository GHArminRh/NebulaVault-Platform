"""Read-only SEO Center overview inside the existing Django admin."""

from django.contrib.auth.decorators import permission_required
from django.db.models import Count
from django.shortcuts import render

from .models import SEOAuditIssue, SEOAuditRun


@permission_required("seo.view_seoauditrun", raise_exception=True)
def seo_dashboard(request):
    latest_run = SEOAuditRun.objects.first()
    recent_runs = SEOAuditRun.objects.all()[:10]
    severity_counts = {}
    latest_issues = SEOAuditIssue.objects.none()

    if latest_run:
        severity_counts = {
            row["severity"]: row["total"]
            for row in latest_run.issues.values("severity").annotate(total=Count("id"))
        }
        latest_issues = latest_run.issues.all()[:20]

    response = render(
        request,
        "admin/seo/dashboard.html",
        {
            "latest_run": latest_run,
            "recent_runs": recent_runs,
            "latest_issues": latest_issues,
            "severity_counts": severity_counts,
            "active_runs": SEOAuditRun.objects.filter(
                status__in=(SEOAuditRun.Status.QUEUED, SEOAuditRun.Status.RUNNING)
            ).count(),
            "total_runs": SEOAuditRun.objects.count(),
        },
    )
    response["Cache-Control"] = "private, no-store"
    return response
