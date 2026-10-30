# Generated migration for the CMS media plugin models.
from django.core.validators import URLValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("cms", "0045_pageurl_site_unique_path"),
    ]

    operations = [
        migrations.CreateModel(
            name="CMSExternalImage",
            fields=[
                (
                    "cmsplugin_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="cms.cmsplugin",
                    ),
                ),
                (
                    "image_url",
                    models.URLField(
                        help_text="برای ماندگاری تصویر، از میزبان رسانه‌ای پایدار استفاده کنید.",
                        max_length=1000,
                        validators=[URLValidator(schemes=["https", "http"])],
                        verbose_name="آدرس تصویر",
                    ),
                ),
                ("alt_text", models.CharField(max_length=240, verbose_name="متن جایگزین")),
                ("caption", models.CharField(blank=True, max_length=320, verbose_name="زیرنویس")),
            ],
            options={
                "verbose_name": "بلوک تصویر خارجی",
                "verbose_name_plural": "بلوک‌های تصویر خارجی",
            },
            bases=("cms.cmsplugin",),
        ),
        migrations.CreateModel(
            name="CMSUploadedImage",
            fields=[
                (
                    "cmsplugin_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="cms.cmsplugin",
                    ),
                ),
                ("image", models.ImageField(upload_to="cms/images/%Y/%m/", verbose_name="فایل تصویر")),
                ("alt_text", models.CharField(max_length=240, verbose_name="متن جایگزین")),
                ("caption", models.CharField(blank=True, max_length=320, verbose_name="زیرنویس")),
            ],
            options={
                "verbose_name": "تصویر بارگذاری‌شدهٔ CMS",
                "verbose_name_plural": "تصاویر بارگذاری‌شدهٔ CMS",
            },
            bases=("cms.cmsplugin",),
        ),
    ]
