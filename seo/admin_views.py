"""Read-only SEO Center overview inside the existing Django admin."""

from django.contrib.auth.decorators import permission_required
from django.db.models import Count, Sum
from django.shortcuts import render

from .models import SEOAuditIssue, SEOAuditRun, SearchConsoleConnection, SearchConsoleMetric


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

    connection = SearchConsoleConnection.objects.filter(is_active=True).first()
    search_console = None
    if connection:
        daily_metrics = SearchConsoleMetric.objects.filter(
            connection=connection,
            dimension_type=SearchConsoleMetric.DimensionType.DAILY,
        ).order_by("-date")[:28]
        totals = daily_metrics.aggregate(clicks=Sum("clicks"), impressions=Sum("impressions"))
        top_queries = SearchConsoleMetric.objects.filter(
            connection=connection,
            dimension_type=SearchConsoleMetric.DimensionType.QUERY,
        ).values("dimension_value").annotate(
            clicks=Sum("clicks"), impressions=Sum("impressions")
        ).order_by("-clicks")[:10]
        top_pages = SearchConsoleMetric.objects.filter(
            connection=connection,
            dimension_type=SearchConsoleMetric.DimensionType.PAGE,
        ).values("dimension_value").annotate(
            clicks=Sum("clicks"), impressions=Sum("impressions")
        ).order_by("-clicks")[:10]
        search_console = {
            "connection": connection,
            "daily_metrics": list(reversed(daily_metrics)),
            "clicks": totals["clicks"] or 0,
            "impressions": totals["impressions"] or 0,
            "top_queries": top_queries,
            "top_pages": top_pages,
        }

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
            "search_console": search_console,
            "google_oauth_configured": bool(
                getattr(__import__("django.conf", fromlist=["settings"]).settings, "GOOGLE_SEARCH_CONSOLE_CLIENT_ID", "")
                and getattr(__import__("django.conf", fromlist=["settings"]).settings, "GOOGLE_SEARCH_CONSOLE_CLIENT_SECRET", "")
            ),
        },
    )
    response["Cache-Control"] = "private, no-store"
    return response
