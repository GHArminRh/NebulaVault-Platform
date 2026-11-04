from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from seo.models import SearchConsoleConnection, SearchConsoleMetric
from seo.search_console import (
    SearchConsoleError,
    decrypt_refresh_token,
    query_search_analytics,
    refresh_access_token,
)


class Command(BaseCommand):
    help = "Sync final daily, query, and page Search Console analytics."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=28)

    def handle(self, *args, **options):
        connection = SearchConsoleConnection.objects.filter(is_active=True).first()
        if not connection:
            raise CommandError("No active Search Console connection exists.")
        days = max(1, min(options["days"], 90))
        # Search Console dates are interpreted in Pacific Time. Exclude the
        # latest three days to avoid presenting still-processing data as final.
        end_date = datetime.now(ZoneInfo("America/Los_Angeles")).date() - timedelta(days=3)
        start_date = end_date - timedelta(days=days - 1)
        try:
            refresh_token = decrypt_refresh_token(connection.refresh_token_encrypted)
            access_token = refresh_access_token(refresh_token)
            saved = 0
            for dimensions, dimension_type in (
                (["date"], SearchConsoleMetric.DimensionType.DAILY),
                (["date", "query"], SearchConsoleMetric.DimensionType.QUERY),
                (["date", "page"], SearchConsoleMetric.DimensionType.PAGE),
            ):
                rows = query_search_analytics(
                    access_token=access_token,
                    site_url=connection.site_url,
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                    dimensions=dimensions,
                )
                for row in rows:
                    keys = row.get("keys", [])
                    if len(keys) != len(dimensions):
                        continue
                    metric_date = date.fromisoformat(keys[0])
                    dimension_value = keys[1] if len(keys) > 1 else ""
                    SearchConsoleMetric.objects.update_or_create(
                        connection=connection,
                        date=metric_date,
                        dimension_type=dimension_type,
                        dimension_value=dimension_value,
                        defaults={
                            "clicks": row.get("clicks", 0),
                            "impressions": row.get("impressions", 0),
                            "ctr": row.get("ctr", 0),
                            "position": row.get("position", 0),
                        },
                    )
                    saved += 1
            connection.last_synced_at = timezone.now()
            connection.last_sync_error = ""
            connection.save(update_fields=["last_synced_at", "last_sync_error"])
        except SearchConsoleError as exc:
            connection.last_sync_error = str(exc)[:4000]
            connection.save(update_fields=["last_sync_error"])
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(
            f"Search Console sync complete: {saved} rows from {start_date} through {end_date}."
        ))
