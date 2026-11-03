from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    """Run Render's release-time Django setup in one Python/Django process."""

    help = "Apply migrations and prepare the database before starting Gunicorn."

    def handle(self, *args, **options):
        verbosity = options["verbosity"]

        self.stdout.write("Applying database migrations...")
        call_command("migrate", interactive=False, verbosity=verbosity)

        # Avoid invoking createcachetable on every restart when the table is
        # already present. This preserves the existing database-cache backend
        # while removing an otherwise unnecessary command and schema check.
        with connection.cursor() as cursor:
            existing_tables = set(connection.introspection.table_names(cursor))

        if "django_cache" not in existing_tables:
            self.stdout.write("Creating the Django database cache table...")
            call_command(
                "createcachetable",
                "django_cache",
                database="default",
                verbosity=verbosity,
            )
        else:
            self.stdout.write("Django database cache table already exists; skipping.")

        self.stdout.write("Preparing Django and Wagtail site configuration...")
        call_command("bootstrap_render_admin", verbosity=verbosity)
        self.stdout.write(self.style.SUCCESS("Render startup preparation completed."))
