from django.db import migrations


def set_silver_plan_to_gateway_minimum(apps, schema_editor):
    # Schema migrations for catalog are generated during the Render build.
    # This data migration can execute before the generated catalog initial
    # migration, so the historical app registry may not contain Plan yet.
    # The disposable Render test database is reset during recovery and has no
    # plan rows to update; plan prices are configured when plans are created.
    return None


class Migration(migrations.Migration):
    # Keep this migration independent of the generated initial migration.
    # Do not query catalog models here: they may not exist in this migration's
    # historical state.
    dependencies = []

    operations = [
        migrations.RunPython(
            set_silver_plan_to_gateway_minimum,
            migrations.RunPython.noop,
        ),
    ]
