import uuid

import sitecms.blocks
import wagtail.fields
import django.db.models.deletion
from django.db import migrations, models


def seed_site_chrome_settings(apps, schema_editor):
    Site = apps.get_model("wagtailcore", "Site")
    SiteChromeSettings = apps.get_model("sitecms", "SiteChromeSettings")
    alias = schema_editor.connection.alias
    site = Site.objects.using(alias).filter(is_default_site=True).first()
    if site is None:
        site = Site.objects.using(alias).first()
    if site is None:
        return

    header_links = [
        ("خانه", "/#home"),
        ("محصولات", "/#products"),
        ("امکانات", "/#features"),
        ("نسخه‌ها", "/#releases"),
        ("بلاگ", "/#blog"),
        ("پرسش‌ها", "/#about"),
    ]
    footer_links = [
        ("محصولات", "/products/"),
        ("بلاگ", "/blog/"),
        ("ورود", "/accounts/login/"),
        ("ثبت‌نام", "/accounts/register/"),
    ]
    SiteChromeSettings.objects.using(alias).get_or_create(
        site_id=site.pk,
        defaults={
            "brand_title": "نبیولا والت",
            "brand_subtitle": "پلتفرم امن نرم‌افزار",
            "brand_mark": "◇",
            "header_links": [
                {
                    "type": "link",
                    "value": {
                        "label": label,
                        "url": url,
                        "open_in_new_tab": False,
                    },
                    "id": str(uuid.uuid4()),
                }
                for label, url in header_links
            ],
            "footer_description": "نرم‌افزارهایی سنجیده و امن، برای آسودگی خاطر شما.",
            "footer_note": "امنیت از ابتدا · پنل حساب و پرداخت",
            "footer_copyright": "",
            "footer_links": [
                {
                    "type": "link",
                    "value": {
                        "label": label,
                        "url": url,
                        "open_in_new_tab": False,
                    },
                    "id": str(uuid.uuid4()),
                }
                for label, url in footer_links
            ],
            "show_install_button": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("sitecms", "0004_editable_homepage_sections"),
        ("wagtailcore", "0098_apitoken"),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteChromeSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "brand_title",
                    models.CharField(
                        default="نبیولا والت",
                        max_length=80,
                        verbose_name="نام برند",
                    ),
                ),
                (
                    "brand_subtitle",
                    models.CharField(
                        default="پلتفرم امن نرم‌افزار",
                        max_length=120,
                        verbose_name="زیرعنوان برند",
                    ),
                ),
                (
                    "brand_mark",
                    models.CharField(
                        default="◇",
                        max_length=4,
                        verbose_name="نماد برند",
                    ),
                ),
                (
                    "header_links",
                    wagtail.fields.StreamField(
                        sitecms.blocks.NavigationMenuBlock(),
                        blank=True,
                        use_json_field=True,
                        verbose_name="پیوندهای سربرگ و منوی موبایل",
                    ),
                ),
                (
                    "footer_description",
                    models.CharField(
                        default="نرم‌افزارهایی سنجیده و امن، برای آسودگی خاطر شما.",
                        max_length=300,
                        verbose_name="توضیحات پابرگ",
                    ),
                ),
                (
                    "footer_note",
                    models.CharField(
                        default="امنیت از ابتدا · پنل حساب و پرداخت",
                        max_length=180,
                        verbose_name="یادداشت پابرگ",
                    ),
                ),
                (
                    "footer_copyright",
                    models.CharField(
                        blank=True,
                        max_length=180,
                        verbose_name="متن حق نشر",
                    ),
                ),
                (
                    "footer_links",
                    wagtail.fields.StreamField(
                        sitecms.blocks.NavigationMenuBlock(),
                        blank=True,
                        use_json_field=True,
                        verbose_name="پیوندهای پابرگ",
                    ),
                ),
                (
                    "show_install_button",
                    models.BooleanField(
                        default=True,
                        verbose_name="نمایش دکمه نصب اپلیکیشن",
                    ),
                ),
                (
                    "site",
                    models.OneToOneField(
                        db_index=True,
                        editable=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="wagtailcore.site",
                    ),
                ),
            ],
            options={
                "verbose_name": "تنظیمات سربرگ و پابرگ",
            },
        ),
        migrations.RunPython(
            seed_site_chrome_settings,
            migrations.RunPython.noop,
        ),
    ]
