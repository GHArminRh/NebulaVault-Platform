import uuid

from django.contrib.auth.models import AbstractUser, Permission
from django.db import models


class Group(models.Model):
    """UUID4-backed staff permission group."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, unique=True)
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name="staff_access_group_set",
        related_query_name="staff_access_group",
    )

    class Meta:
        verbose_name = "group"
        verbose_name_plural = "groups"
        ordering = ["name"]

    def __str__(self):
        return self.name


class StaffUser(AbstractUser):
    """Internal staff/admin identity with UUID4 primary key."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    groups = models.ManyToManyField(
        "staff_access.Group",
        blank=True,
        related_name="user_set",
        related_query_name="user",
        help_text="The groups this staff user belongs to.",
    )

    class Meta:
        verbose_name = "staff user"
        verbose_name_plural = "staff users"
