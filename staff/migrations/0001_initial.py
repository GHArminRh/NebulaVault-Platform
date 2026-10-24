# Generated for the UUID-backed staff user model.
import uuid

import django.contrib.auth.models
import django.contrib.auth.validators
import django.utils.timezone
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="Group",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=150, unique=True)),
                (
                    "permissions",
                    models.ManyToManyField(
                        blank=True,
                        db_table="accounts_group_permissions",
                        related_name="accounts_group_set",
                        related_query_name="accounts_group",
                        to="auth.permission",
                    ),
                ),
            ],
            options={
                "db_table": "accounts_group",
                "verbose_name": "group",
                "verbose_name_plural": "groups",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="StaffUser",
            fields=[
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False, help_text="Designates that this user has all permissions without explicitly assigning them.", verbose_name="superuser status")),
                ("username", models.CharField(
                    error_messages={"unique": "A user with that username already exists."},
                    help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
                    max_length=150,
                    unique=True,
                    validators=[django.contrib.auth.validators.UnicodeUsernameValidator()],
                    verbose_name="username",
                )),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="email address")),
                ("is_staff", models.BooleanField(default=False, help_text="Designates whether the user can log into this admin site.", verbose_name="staff status")),
                ("is_active", models.BooleanField(default=True, help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.", verbose_name="active")),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined")),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        db_table="accounts_staffuser_groups",
                        help_text="The groups this staff user belongs to.",
                        related_name="user_set",
                        related_query_name="user",
                        to="staff.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        db_table="accounts_staffuser_user_permissions",
                        related_name="user_set",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "db_table": "accounts_staffuser",
                "verbose_name": "staff user",
                "verbose_name_plural": "staff users",
            },
            managers=[
                ("objects", django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
