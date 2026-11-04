from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from seo.models import SEOAuditIssue, SEOAuditRun
from seo.services.crawler import CrawlError, SiteCrawler


class Command(BaseCommand):
    help = "Run a bounded technical SEO crawl against SITE_BASE_URL."

    def add_arguments(self, parser):
        parser.add_argument("--max-pages", type=int, default=150)
        parser.add_argument("--timeout", type=int, default=8)
        parser.add_argument("--request-delay", type=float, default=0.2)
        parser.add_argument("--max-duration", type=int, default=180)
        parser.add_argument("--run-id", type=int)

    def handle(self, *args, **options):
        run_id = options.get("run_id")
        if run_id:
            try:
                run = SEOAuditRun.objects.get(pk=run_id)
            except SEOAuditRun.DoesNotExist as exc:
                raise CommandError(f"SEO audit run {run_id} does not exist.") from exc
            if run.status == SEOAuditRun.Status.RUNNING:
                raise CommandError(f"SEO audit run {run_id} is already running.")
            run.issues.all().delete()
        else:
            run = SEOAuditRun.objects.create()

        run.status = SEOAuditRun.Status.RUNNING
        run.started_at = timezone.now()
        run.completed_at = None
        run.error_message = ""
        run.save(update_fields=["status", "started_at", "completed_at", "error_message"])

        try:
            result = SiteCrawler(
                max_pages=options["max_pages"],
                timeout=options["timeout"],
                request_delay=options["request_delay"],
                max_duration_seconds=options["max_duration"],
            ).crawl()
            SEOAuditIssue.objects.bulk_create(
                [
                    SEOAuditIssue(run=run, **issue)
                    for issue in result["issues"]
                ],
                batch_size=500,
            )
            run.pages_scanned = result["pages_scanned"]
            run.issues_count = len(result["issues"])
            run.status = SEOAuditRun.Status.COMPLETED
            run.completed_at = timezone.now()
            run.save(
                update_fields=[
                    "pages_scanned",
                    "issues_count",
                    "status",
                    "completed_at",
                ]
            )
        except Exception as exc:
            run.status = SEOAuditRun.Status.FAILED
            run.completed_at = timezone.now()
            run.error_message = str(exc)[:4000]
            run.save(update_fields=["status", "completed_at", "error_message"])
            if isinstance(exc, CrawlError):
                raise CommandError(str(exc)) from exc
            raise

        self.stdout.write(
            self.style.SUCCESS(
                f"SEO audit #{run.pk} completed: "
                f"{run.pages_scanned} pages, {run.issues_count} issues."
            )
        )
