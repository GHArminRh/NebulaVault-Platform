from django.conf import settings
from django.db import migrations, models
import django.utils.timezone
import uuid
import accounts.models


def ensure_account_tables_and_ban_field(apps, schema_editor):
    # This app previously had no migration files, so existing installations may
    # already have tables created by migrate --run-syncdb while fresh installs
    # may not. Support both states without recreating existing customer data.
    from accounts.models import Customer, AccountEmailLog

    connection = schema_editor.connection
    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names(cursor))

    if Customer._meta.db_table not in tables:
        schema_editor.create_model(Customer)
    else:
        existing_columns = {
            column.name for column in connection.introspection.get_table_description(
                connection.cursor(), Customer._meta.db_table
            )
        }
        if "is_banned" not in existing_columns:
            schema_editor.add_field(Customer, Customer._meta.get_field("is_banned"))

    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names(cursor))
    if AccountEmailLog._meta.db_table not in tables:
        schema_editor.create_model(AccountEmailLog)


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    ensure_account_tables_and_ban_field,
                    reverse_code=migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.CreateModel(
                    name="Customer",
                    fields=[
                        ("password", models.CharField(max_length=128, verbose_name="password")),
                        ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ("email", models.EmailField(max_length=254, unique=True)),
                        ("username", models.CharField(max_length=150, unique=True)),
                        ("first_name", models.CharField(blank=True, max_length=150)),
                        ("last_name", models.CharField(blank=True, max_length=150)),
                        ("is_active", models.BooleanField(default=True)),
                        ("is_banned", models.BooleanField(default=False, help_text="Blocked by an administrator; the customer cannot sign in.")),
                        ("date_joined", models.DateTimeField(auto_now_add=True)),
                    ],
                    options={
                        "verbose_name": "customer",
                        "verbose_name_plural": "customers",
                        "ordering": ["-date_joined"],
                    },
                    managers=[("objects", accounts.models.CustomerManager())],
                ),
                migrations.CreateModel(
                    name="AccountEmailLog",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("recipient", models.EmailField(db_index=True, max_length=254)),
                        ("purpose", models.CharField(choices=[("verification", "Email verification"), ("password_reset", "Password recovery")], db_index=True, max_length=24)),
                        ("status", models.CharField(choices=[("sent", "Sent"), ("failed", "Failed"), ("throttled", "Rate limited"), ("used", "Code used"), ("expired", "Expired"), ("superseded", "Replaced by a newer email")], db_index=True, default="sent", max_length=16)),
                        ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                        ("sent_at", models.DateTimeField(blank=True, null=True)),
                        ("expires_at", models.DateTimeField(blank=True, null=True)),
                        ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                        ("code_hash", models.CharField(blank=True, editable=False, max_length=64)),
                        ("failed_attempts", models.PositiveSmallIntegerField(default=0)),
                        ("consumed_at", models.DateTimeField(blank=True, null=True)),
                        ("error_message", models.TextField(blank=True)),
                        ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="email_history", to="accounts.customer")),
                    ],
                    options={
                        "verbose_name": "account email history",
                        "verbose_name_plural": "account email history",
                        "ordering": ["-created_at"],
                    },
                ),
            ],
        ),
    ]
