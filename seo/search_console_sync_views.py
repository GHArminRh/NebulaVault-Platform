"""Staff-only manual Search Console sync action for the SEO Center."""

from io import StringIO

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import permission_required
from django.core.management import call_command, CommandError
from django.db import transaction
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from .models import SearchConsoleConnection


@permission_required("seo.view_seoauditrun", raise_exception=True)
@staff_member_required
@require_POST
def search_console_sync_now(request):
    """Run the existing sync command from an authenticated admin POST.

    The active connection row is locked for the duration of the sync. On the
    production PostgreSQL database this serializes concurrent requests across
    web workers without relying on process-local locks or a cache table.
    """
    output = StringIO()
    sync_error = ""

    try:
        with transaction.atomic():
            connection = (
                SearchConsoleConnection.objects.select_for_update()
                .filter(is_active=True)
                .first()
            )
            if connection is None:
                messages.error(request, "No active Google Search Console property is connected.")
                return redirect("seo-dashboard")

            # Catch CommandError inside the transaction so the command's
            # last_sync_error update is committed instead of rolled back.
            try:
                call_command("sync_search_console", days=28, stdout=output)
            except CommandError as exc:
                sync_error = str(exc)
    except Exception:
        # Do not expose tracebacks, credentials, or provider response bodies in
        # the admin UI. Detailed diagnostics remain in the server error logs.
        messages.error(
            request,
            "Search Console sync failed unexpectedly. Check the application logs for details.",
        )
    else:
        if sync_error:
            messages.error(request, f"Search Console sync failed: {sync_error}")
        else:
            result = output.getvalue().strip()
            messages.success(
                request,
                result or "Google Search Console synchronization completed successfully.",
            )

    return redirect("seo-dashboard")
