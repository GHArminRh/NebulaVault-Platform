import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerAPIToken",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("token_prefix", models.CharField(db_index=True, max_length=12)),
                ("token_digest", models.CharField(max_length=64, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("customer", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="api_tokens",
                    to="accounts.customer",
                )),
            ],
            options={
                "verbose_name": "customer API token",
                "verbose_name_plural": "customer API tokens",
                "ordering": ("-created_at",),
                "indexes": [
                    models.Index(fields=["customer", "revoked_at"], name="api_cust_revoke_idx"),
                ],
            },
        ),
    ]
