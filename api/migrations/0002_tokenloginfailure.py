import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TokenLoginFailure",
            fields=[
                (
                    "email_digest",
                    models.CharField(max_length=64, primary_key=True, serialize=False),
                ),
                ("failed_attempts", models.PositiveIntegerField(default=0)),
                ("window_started_at", models.DateTimeField()),
                ("locked_until", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={
                "verbose_name": "API token login failure counter",
                "verbose_name_plural": "API token login failure counters",
            },
        ),
    ]
