import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Create or refresh the Render bootstrap admin only when a secret is supplied.

    Set NEBULA_BOOTSTRAP_ADMIN_PASSWORD temporarily in the Render environment.
    With the variable absent or empty, this command does nothing.
    """

    help = "Create or refresh the bootstrap admin from a temporary environment secret."

    def handle(self, *args, **options):
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
