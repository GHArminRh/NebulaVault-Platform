import uuid

from django.contrib.auth.models import AbstractUser, Permission
from django.db import models


class Group(models.Model):
    """UUID-backed permission group for staff accounts."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, unique=True)
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name="accounts_group_set",
        related_query_name="accounts_group",
        db_table="accounts_group_permissions",
    )

    class Meta:
        db_table = "accounts_group"
        verbose_name = "group"
        verbose_name_plural = "groups"
        ordering = ["name"]

    def __str__(self):
        return self.name


class StaffUser(AbstractUser):
    """UUID-backed Django identity for staff and admin access."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    groups = models.ManyToManyField(
        Group,
        blank=True,
        related_name="user_set",
        related_query_name="user",
        help_text="The groups this staff user belongs to.",
        db_table="accounts_staffuser_groups",
    )
    # Wagtail maintains page and collection permissions against Django auth.Group.
    # Keep those roles separate from the project UUID-backed staff.Group model.
    wagtail_groups = models.ManyToManyField(
        "auth.Group",
        blank=True,
        related_name="user_set",
        related_query_name="user",
        db_table="accounts_staffuser_wagtail_groups",
        help_text="The Wagtail groups this staff user belongs to.",
    )

    user_permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name="user_set",
        related_query_name="user",
        db_table="accounts_staffuser_user_permissions",
    )

    class Meta:
        db_table = "accounts_staffuser"
        verbose_name = "staff user"
        verbose_name_plural = "staff users"
