from django.apps import AppConfig


class PortalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "portal"

    def ready(self):
        # The Render service's dashboard start command may not be synchronized
        # with render.yaml. Run the idempotent CMS bootstrap after migrations so
        # an existing empty homepage is completed without overwriting editor content.
        from django.contrib.sites.models import Site
        from django.core.management import call_command
        from django.db.models.signals import post_migrate

        def ensure_cms_homepage(sender, **kwargs):
            from django.conf import settings

            if not Site.objects.filter(pk=settings.SITE_ID).exists():
                return
            call_command("bootstrap_cms_homepage", verbosity=0)

        post_migrate.connect(
            ensure_cms_homepage,
            sender=self,
            dispatch_uid="portal.ensure_cms_homepage",
            weak=False,
        )
