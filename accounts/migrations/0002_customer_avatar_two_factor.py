import accounts.validators
from django.db import migrations, models


def ensure_customer_security_fields(apps, schema_editor):
    # Some existing deployments created app tables with syncdb before migrations
    # were introduced. Avoid adding a column twice in those databases.
    from accounts.models import Customer

    connection = schema_editor.connection
    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names(cursor))
    if Customer._meta.db_table not in tables:
        return

    with connection.cursor() as cursor:
        columns = {
            column.name
            for column in connection.introspection.get_table_description(
                cursor, Customer._meta.db_table
            )
        }
    for field_name in ("avatar", "two_factor_enabled", "two_factor_secret"):
        if field_name not in columns:
            schema_editor.add_field(Customer, Customer._meta.get_field(field_name))


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    ensure_customer_security_fields,
                    reverse_code=migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="customer",
                    name="avatar",
                    field=models.ImageField(
                        blank=True,
                        upload_to=accounts.validators.avatar_upload_to,
                        validators=[accounts.validators.validate_avatar_size],
                    ),
                ),
                migrations.AddField(
                    model_name="customer",
                    name="two_factor_enabled",
                    field=models.BooleanField(default=False),
                ),
                migrations.AddField(
                    model_name="customer",
                    name="two_factor_secret",
                    field=models.CharField(blank=True, editable=False, max_length=255),
                ),
            ],
        ),
    ]
