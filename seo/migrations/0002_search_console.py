from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("seo", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="SearchConsoleConnection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("site_url", models.CharField(max_length=255, unique=True)),
                ("connected_email", models.EmailField(blank=True, max_length=254)),
                ("refresh_token_encrypted", models.TextField()),
                ("granted_scope", models.TextField(blank=True)),
                ("connected_at", models.DateTimeField(auto_now_add=True)),
                ("last_synced_at", models.DateTimeField(blank=True, null=True)),
                ("last_sync_error", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"verbose_name": "Search Console connection", "verbose_name_plural": "Search Console connections"},
        ),
        migrations.CreateModel(
            name="SearchConsoleMetric",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(db_index=True)),
                ("dimension_type", models.CharField(choices=[("daily", "Daily"), ("query", "Query"), ("page", "Page")], max_length=8)),
                ("dimension_value", models.CharField(blank=True, max_length=2048)),
                ("clicks", models.FloatField(default=0)),
                ("impressions", models.FloatField(default=0)),
                ("ctr", models.FloatField(default=0)),
                ("position", models.FloatField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("connection", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="metrics", to="seo.searchconsoleconnection")),
            ],
            options={"ordering": ("date", "dimension_type", "dimension_value"), "indexes": [models.Index(fields=["connection", "dimension_type", "date"], name="seo_gsc_type_date_idx")], "constraints": [models.UniqueConstraint(fields=("connection", "date", "dimension_type", "dimension_value"), name="seo_gsc_metric_unique")]},
        ),
    ]
