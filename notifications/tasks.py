"""Small operational tasks used to verify the background worker."""

from celery import shared_task


@shared_task(name="notifications.celery_healthcheck", ignore_result=True)
def celery_healthcheck(probe_id: str) -> dict[str, object]:
    """Verify worker execution, database access, and shared cache visibility."""
    from django.core.cache import cache
    from django.db import connection
    from django.utils import timezone

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        database_ok = cursor.fetchone()[0] == 1

    result = {
        "ok": database_ok,
        "database": "ok" if database_ok else "failed",
        "completed_at": timezone.now().isoformat(),
    }
    cache.set(f"celery:healthcheck:{probe_id}", result, timeout=120)
    return result
