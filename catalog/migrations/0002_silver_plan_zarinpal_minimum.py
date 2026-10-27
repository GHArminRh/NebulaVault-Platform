from django.db import migrations


def set_silver_plan_to_gateway_minimum(apps, schema_editor):
    Plan = apps.get_model("catalog", "Plan")
    # Catalog prices are stored in hundredths of the displayed currency.
    # 100,000 stored units => 1,000 Rials after the gateway conversion.
    Plan.objects.filter(
        name="اشتراک نقره ای",
        currency="IRR",
        price_minor_units=10000,
        is_active=True,
    ).update(price_minor_units=100000)


class Migration(migrations.Migration):
    # This repository intentionally does not track catalog schema migrations;
    # the production database already has the catalog tables. Keep this
    # data-only migration independent of the historical, untracked initial
    # migration so Django can build a consistent graph during deployment.
    dependencies = []

    operations = [
        migrations.RunPython(
            set_silver_plan_to_gateway_minimum,
            migrations.RunPython.noop,
        ),
    ]
