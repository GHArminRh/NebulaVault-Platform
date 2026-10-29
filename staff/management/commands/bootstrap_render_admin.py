import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Repair the required primary Site and optionally bootstrap the Render admin.

    Set NEBULA_BOOTSTRAP_ADMIN_PASSWORD temporarily in the Render environment.
    With the variable absent or empty, admin bootstrap is skipped, but the
    required Django Site row is still repaired before the web server starts.
    """

    help = "Ensure the primary Django Site and optionally bootstrap the Render admin."

    def handle(self, *args, **options):
        site_id = getattr(settings, "SITE_ID", 1)
        Site.objects.update_or_create(
            pk=site_id,
            defaults={"domain": "mydigigi.ir", "name": "Nebula Vault"},
        )
        self.stdout.write(self.style.SUCCESS(f"Primary Django Site {site_id} is ready."))

        # The Render service's configured start command already invokes this
        # command. Bootstrap the editable CMS homepage here as well, so the
        # live service does not depend on a Blueprint sync to pick up changes
        # made to render.yaml's startCommand.
        call_command("bootstrap_cms_homepage")

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
