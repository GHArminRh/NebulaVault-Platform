"""Queue a real Celery task and wait for its worker-side completion marker."""

import time
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError

from notifications.tasks import celery_healthcheck


class Command(BaseCommand):
    help = "Verify Celery broker connectivity and worker task execution."

    def add_arguments(self, parser):
        parser.add_argument("--timeout", type=int, default=30)

    def handle(self, *args, **options):
        if not getattr(settings, "CELERY_BROKER_URL", ""):
            raise CommandError("CELERY_BROKER_URL is not configured.")

        probe_id = uuid4().hex
        cache_key = f"celery:healthcheck:{probe_id}"
        cache.delete(cache_key)
        try:
            async_result = celery_healthcheck.apply_async(args=[probe_id])
        except Exception as exc:
            raise CommandError(f"Could not enqueue the Celery task: {exc}") from exc

        deadline = time.monotonic() + max(1, options["timeout"])
        result = None
        while time.monotonic() < deadline:
            result = cache.get(cache_key)
            if result is not None:
                break
            time.sleep(0.25)

        if result is None:
            raise CommandError(
                f"Task {async_result.id} was queued but no worker completion marker "
                f"arrived within {options['timeout']} seconds."
            )
        if not result.get("ok"):
            raise CommandError(f"Worker task reported a failure: {result}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Celery worker OK; task_id={async_result.id}; "
                f"database={result['database']}; completed_at={result['completed_at']}"
            )
        )
