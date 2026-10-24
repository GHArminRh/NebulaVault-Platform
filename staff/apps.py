from django.apps import AppConfig


class StaffConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "staff"
    verbose_name = "Staff & Permissions"

    def ready(self):
        from django.db.models.signals import pre_migrate
        from .signals import migrate_legacy_content_types

        pre_migrate.connect(
            migrate_legacy_content_types,
            dispatch_uid="staff.migrate_legacy_content_types",
        )
