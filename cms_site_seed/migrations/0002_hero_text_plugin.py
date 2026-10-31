"""Upgrade existing homepage hero text plugins without rewriting editor content."""

from django.db import migrations


def upgrade_hero_text_plugins(apps, schema_editor):
    CMSPlugin = apps.get_model("cms", "CMSPlugin")
    CMSPlugin.objects.filter(
        placeholder__slot="hero",
        language="fa",
        plugin_type="TextPlugin",
    ).update(plugin_type="HeroTextPlugin")


def downgrade_hero_text_plugins(apps, schema_editor):
    CMSPlugin = apps.get_model("cms", "CMSPlugin")
    CMSPlugin.objects.filter(
        placeholder__slot="hero",
        language="fa",
        plugin_type="HeroTextPlugin",
    ).update(plugin_type="TextPlugin")


class Migration(migrations.Migration):
    dependencies = [
        ("cms_site_seed", "0001_seed_empty_homepage_regions"),
    ]

    operations = [
        migrations.RunPython(
            upgrade_hero_text_plugins,
            downgrade_hero_text_plugins,
        ),
    ]
