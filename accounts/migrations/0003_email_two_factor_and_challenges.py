from django.db import migrations, models


def ensure_customer_email_security_fields(apps, schema_editor):
    from accounts.models import Customer

    connection = schema_editor.connection
    with connection.cursor() as cursor:
        columns = {
            column.name
            for column in connection.introspection.get_table_description(
                cursor, Customer._meta.db_table
            )
        }
    for field_name in ("email_two_factor_enabled", "recovery_codes"):
        if field_name not in columns:
            schema_editor.add_field(Customer, Customer._meta.get_field(field_name))


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_customer_avatar_two_factor"),
        ("staff", "0004_staffuser_avatar_two_factor"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    ensure_customer_email_security_fields,
                    reverse_code=migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="customer",
                    name="email_two_factor_enabled",
                    field=models.BooleanField(default=False),
                ),
                migrations.AddField(
                    model_name="customer",
                    name="recovery_codes",
                    field=models.JSONField(blank=True, default=list, editable=False),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TwoFactorEmailChallenge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_type", models.CharField(db_index=True, max_length=80)),
                ("user_id", models.CharField(db_index=True, max_length=36)),
                ("recipient", models.EmailField(max_length=254)),
                ("purpose", models.CharField(choices=[("login", "Login"), ("setup", "Enrollment")], db_index=True, max_length=8)),
                ("code_hash", models.CharField(editable=False, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("failed_attempts", models.PositiveSmallIntegerField(default=0)),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["user_type", "user_id", "purpose", "created_at"], name="accounts_tw_user_ty_b7bb41_idx"),
                ],
            },
        ),
    ]
