"""Compatibility helpers for moving staff models out of accounts."""

from django.db import connections


def migrate_legacy_content_types(sender, using, **kwargs):
    """Keep existing permission rows attached to the moved staff models."""
    if getattr(sender, "name", None) != "staff":
        return

    connection = connections[using]
    if "django_content_type" not in connection.introspection.table_names():
        return

    from django.contrib.contenttypes.models import ContentType

    legacy = ContentType.objects.using(using).filter(
        app_label="accounts", model__in=("group", "staffuser")
    )
    for content_type in legacy:
        already_exists = ContentType.objects.using(using).filter(
            app_label="staff", model=content_type.model
        ).exclude(pk=content_type.pk).exists()
        if not already_exists:
            ContentType.objects.using(using).filter(pk=content_type.pk).update(
                app_label="staff"
            )
