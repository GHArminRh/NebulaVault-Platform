"""Authenticated HTTP trigger for Wagtail's scheduled publishing command."""

import logging
import secrets
from contextlib import contextmanager
from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

# Stable application-specific PostgreSQL advisory-lock key.
_PUBLISH_LOCK_KEY = 7_214_603_119


@contextmanager
def _publishing_lock():
    """Prevent overlapping runs across web workers on PostgreSQL."""
    if connection.vendor != "postgresql":
        # Non-PostgreSQL databases are used only for local/test environments.
        yield True
        return

    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [_PUBLISH_LOCK_KEY])
        acquired = bool(cursor.fetchone()[0])

    try:
        yield acquired
    finally:
        if acquired:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_advisory_unlock(%s)", [_PUBLISH_LOCK_KEY]
                )


@csrf_exempt
@require_POST
def publish_scheduled_pages(request):
    """Run Wagtail scheduled publishing after validating a shared bearer secret."""
    expected_secret = getattr(settings, "WAGTAIL_CRON_SECRET", "").strip()
    if len(expected_secret) < 32:
        logger.error("Wagtail scheduled-publishing endpoint is not configured.")
        return JsonResponse(
            {"status": "unavailable", "detail": "Scheduler is not configured."},
            status=503,
        )

    authorization = request.headers.get("Authorization", "")
    scheme, separator, supplied_secret = authorization.partition(" ")
    if (
        not separator
        or scheme.lower() != "bearer"
        or not secrets.compare_digest(supplied_secret, expected_secret)
    ):
        return JsonResponse({"status": "unauthorized"}, status=403)

    with _publishing_lock() as acquired:
        if not acquired:
            return JsonResponse(
                {"status": "already_running"},
                status=409,
            )

        output = StringIO()
        try:
            call_command("publish_scheduled", stdout=output, stderr=output)
        except Exception:
            logger.exception("Wagtail scheduled publishing failed.")
            return JsonResponse(
                {"status": "error", "detail": "Scheduled publishing failed."},
                status=500,
            )

    # Keep the response deliberately small for hosted HTTP schedulers.
    return JsonResponse(
        {
            "status": "ok",
            "command": "publish_scheduled",
            "output": output.getvalue()[-2000:],
        },
        status=200,
    )
