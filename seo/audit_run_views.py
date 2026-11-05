"""Staff-only, one-click technical SEO audit runner for the admin dashboard."""

import logging
from io import StringIO

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import permission_required
from django.core.management import CommandError, call_command
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


@permission_required("seo.view_seoauditrun", raise_exception=True)
@staff_member_required
@require_POST
def seo_audit_run_now(request):
    """Run a bounded crawl without requiring access to the Render shell."""
    output = StringIO()
    try:
        call_command(
            "run_seo_audit",
            max_pages=100,
            timeout=8,
            request_delay=0.2,
            max_duration=60,
            stdout=output,
        )
    except CommandError as exc:
        messages.error(request, f"Technical SEO audit failed: {exc}")
    except Exception:
        logger.exception("Unexpected error while running the technical SEO audit.")
        messages.error(
            request,
            "Technical SEO audit failed unexpectedly. Check the application logs for details.",
        )
    else:
        messages.success(
            request,
            output.getvalue().strip() or "Technical SEO audit completed successfully.",
        )
    return redirect("seo-dashboard")
