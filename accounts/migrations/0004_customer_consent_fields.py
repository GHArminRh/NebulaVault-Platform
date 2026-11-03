from django.db import migrations, models


def ensure_customer_consent_fields(apps, schema_editor):
    # accounts.0001 may create the live Customer model dynamically on a fresh
    # database. That can already include fields added after the historical
    # migration state, so only add columns that are genuinely missing.
    from accounts.models import Customer

    connection = schema_editor.connection
    with connection.cursor() as cursor:
        columns = {
            column.name
            for column in connection.introspection.get_table_description(
                cursor, Customer._meta.db_table
            )
        }

    for field_name in (
        "terms_accepted_at",
        "terms_version",
        "newsletter_opt_in",
        "newsletter_opt_in_at",
    ):
        if field_name not in columns:
            schema_editor.add_field(
                Customer,
                Customer._meta.get_field(field_name),
            )


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_email_two_factor_and_challenges")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    ensure_customer_consent_fields,
                    reverse_code=migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="customer",
                    name="terms_accepted_at",
                    field=models.DateTimeField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="customer",
                    name="terms_version",
                    field=models.CharField(blank=True, max_length=32),
                ),
                migrations.AddField(
                    model_name="customer",
                    name="newsletter_opt_in",
                    field=models.BooleanField(default=False),
                ),
                migrations.AddField(
                    model_name="customer",
                    name="newsletter_opt_in_at",
                    field=models.DateTimeField(blank=True, null=True),
                ),
            ],
        ),
    ]
