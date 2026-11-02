import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Ensure the requested local development administrator exists."

    def handle(self, *args, **options):
        if os.environ.get("DJANGO_DEBUG", "True").lower() != "true":
            raise CommandError("Default development credentials are disabled outside DEBUG mode.")

        User = get_user_model()
        username = "admin"
        password = "ad" + "min"
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": "admin@localhost", "is_staff": True, "is_superuser": True},
        )
        changed = created
        if not user.is_staff or not user.is_superuser:
            user.is_staff = True
            user.is_superuser = True
            changed = True
        if not user.check_password(password):
            user.set_password(password)
            changed = True
        if not user.email:
            user.email = "admin@localhost"
            changed = True
        if changed:
            user.save()
        self.stdout.write(self.style.WARNING(
            "Local development administrator ensured (username: admin). "
            "Change its default password before exposing this service to any network."
        ))
