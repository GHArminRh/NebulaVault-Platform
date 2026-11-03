import os
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from wagtail.models import Site as WagtailSite


class Command(BaseCommand):
    """Repair the required primary Site and optionally bootstrap the Render admin.

    Set NEBULA_BOOTSTRAP_ADMIN_PASSWORD temporarily in the Render environment.
    With the variable absent or empty, admin bootstrap is skipped, but the
    required Django Site row is still repaired before the web server starts.
    """

    help = "Ensure the primary Django Site and optionally bootstrap the Render admin."

    def handle(self, *args, **options):
        site_id = getattr(settings, "SITE_ID", 1)
        canonical_url = urlsplit(settings.SITE_BASE_URL)
        canonical_domain = canonical_url.netloc
        Site.objects.update_or_create(
            pk=site_id,
            defaults={"domain": canonical_domain, "name": "Nebula Vault"},
        )
        # Wagtail uses its own Site model to build absolute page and sitemap URLs.
        # Update the existing default Wagtail site without changing its root page.
        WagtailSite.objects.filter(is_default_site=True).update(
            hostname=canonical_url.hostname,
            port=canonical_url.port or (443 if canonical_url.scheme == "https" else 80),
        )
        self.stdout.write(self.style.SUCCESS(f"Primary Django Site {site_id} is ready."))

        # Optional one-time Algolia bootstrap. Render runs this command after
        # migrations and cache-table creation; a persistent DB-cache marker
        # prevents reindexing on every subsequent restart.
        reindex_token = os.environ.get("ALGOLIA_REINDEX_ON_BOOT", "").strip()
        if reindex_token:
            from django.core.cache import cache
            from django.core.management import call_command

            cache_key = f"nebula:algolia:reindex:{reindex_token[:160]}"
            if cache.get(cache_key) == "done":
                self.stdout.write("Algolia bootstrap reindex already completed.")
            elif cache.add(cache_key, "running", timeout=900):
                try:
                    call_command("reindex_algolia")
                except Exception:
                    cache.delete(cache_key)
                    raise
                cache.set(cache_key, "done", timeout=None)
            else:
                self.stdout.write("Algolia bootstrap reindex is already running.")

        password = os.environ.get("NEBULA_BOOTSTRAP_ADMIN_PASSWORD", "")
        if not password:
            self.stdout.write("Bootstrap admin skipped: no temporary password configured.")
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"Bootstrap admin {action} successfully."))
