from django.db import migrations, models


def ensure_staff_email_security_fields(apps, schema_editor):
    from staff.models import StaffUser

    connection = schema_editor.connection
    with connection.cursor() as cursor:
        columns = {
            column.name
            for column in connection.introspection.get_table_description(
                cursor, StaffUser._meta.db_table
            )
        }
    for field_name in ("email_two_factor_enabled", "recovery_codes"):
        if field_name not in columns:
            schema_editor.add_field(StaffUser, StaffUser._meta.get_field(field_name))


class Migration(migrations.Migration):
    dependencies = [
        ("staff", "0004_staffuser_avatar_two_factor"),
        ("accounts", "0003_email_two_factor_and_challenges"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    ensure_staff_email_security_fields,
                    reverse_code=migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="staffuser",
                    name="email_two_factor_enabled",
                    field=models.BooleanField(default=False),
                ),
                migrations.AddField(
                    model_name="staffuser",
                    name="recovery_codes",
                    field=models.JSONField(blank=True, default=list, editable=False),
                ),
            ],
        ),
    ]
