from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0003_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="seo_title",
            field=models.CharField(
                blank=True,
                help_text="Optional search-result title; falls back to the product name.",
                max_length=220,
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="seo_description",
            field=models.CharField(
                blank=True,
                help_text="Optional search description; falls back to the product description.",
                max_length=320,
            ),
        ),
    ]
