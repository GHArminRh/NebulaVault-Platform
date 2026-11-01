import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_customer_avatar_two_factor"),
        ("staff", "0004_staffuser_avatar_two_factor"),
    ]

    operations = [
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
                    models.Index(fields=["user_type", "user_id", "purpose", "created_at"], name="accounts_tft_user_purpose_idx"),
                ],
            },
        ),
    ]
