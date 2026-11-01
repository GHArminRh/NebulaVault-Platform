import sitecms.blocks
import wagtail.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("sitecms", "0002_convert_default_homepage"),
    ]

    operations = [
        migrations.AddField(
            model_name="homepage",
            name="sections",
            field=wagtail.fields.StreamField(
                sitecms.blocks.NebulaContentBlock(),
                blank=True,
                use_json_field=True,
                verbose_name="بخش‌های قابل چیدمان صفحه اصلی",
            ),
        ),
        migrations.AddField(
            model_name="contentpage",
            name="sections",
            field=wagtail.fields.StreamField(
                sitecms.blocks.NebulaContentBlock(),
                blank=True,
                use_json_field=True,
                verbose_name="بخش‌های محتوایی صفحه",
            ),
        ),
    ]
