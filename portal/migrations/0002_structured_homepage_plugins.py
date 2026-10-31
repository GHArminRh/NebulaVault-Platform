# Generated for the structured django CMS homepage plugins.
import django.db.models.deletion
from django.db import migrations, models

import portal.models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CMSHeroContent",
            fields=[
                ("cmsplugin_ptr", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    parent_link=True,
                    primary_key=True,
                    related_name="portal_hero_content",
                    to="cms.cmsplugin",
                )),
                ("eyebrow", models.CharField(blank=True, default="", max_length=180, verbose_name="متن بالای عنوان")),
                ("heading", models.CharField(blank=True, default="", max_length=200, verbose_name="عنوان اصلی")),
                ("heading_accent", models.CharField(blank=True, default="", max_length=200, verbose_name="عبارت رنگی عنوان")),
                ("description", models.TextField(blank=True, default="", verbose_name="توضیح کوتاه")),
                ("primary_cta_label", models.CharField(blank=True, default="", max_length=80, verbose_name="متن دکمهٔ اصلی")),
                ("primary_cta_url", models.CharField(blank=True, default="", max_length=500, validators=[portal.models.validate_cms_link], verbose_name="پیوند دکمهٔ اصلی")),
                ("secondary_cta_label", models.CharField(blank=True, default="", max_length=80, verbose_name="متن دکمهٔ دوم")),
                ("secondary_cta_url", models.CharField(blank=True, default="", max_length=500, validators=[portal.models.validate_cms_link], verbose_name="پیوند دکمهٔ دوم")),
                ("trust_item_1", models.CharField(blank=True, default="", max_length=120, verbose_name="نکتهٔ اعتماد ۱")),
                ("trust_item_2", models.CharField(blank=True, default="", max_length=120, verbose_name="نکتهٔ اعتماد ۲")),
                ("trust_item_3", models.CharField(blank=True, default="", max_length=120, verbose_name="نکتهٔ اعتماد ۳")),
                ("legacy_source", models.TextField(blank=True, default="", editable=False, verbose_name="نسخهٔ پشتیبان محتوای قبلی")),
            ],
            options={
                "verbose_name": "محتوای ساختاریافتهٔ بنر اصلی",
                "verbose_name_plural": "محتوای ساختاریافتهٔ بنر اصلی",
            },
            bases=("cms.cmsplugin",),
        ),
        migrations.CreateModel(
            name="CMSFeatureGrid",
            fields=[
                ("cmsplugin_ptr", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    parent_link=True,
                    primary_key=True,
                    related_name="portal_feature_grid",
                    to="cms.cmsplugin",
                )),
                ("feature_1_icon", models.CharField(blank=True, default="", max_length=24, verbose_name="نماد ویژگی ۱")),
                ("feature_1_number", models.CharField(blank=True, default="", max_length=8, verbose_name="شمارهٔ ویژگی ۱")),
                ("feature_1_title", models.CharField(blank=True, default="", max_length=140, verbose_name="عنوان ویژگی ۱")),
                ("feature_1_description", models.TextField(blank=True, default="", verbose_name="توضیح ویژگی ۱")),
                ("feature_1_link_label", models.CharField(blank=True, default="", max_length=100, verbose_name="متن پیوند ویژگی ۱")),
                ("feature_1_link_url", models.CharField(blank=True, default="", max_length=500, validators=[portal.models.validate_cms_link], verbose_name="پیوند ویژگی ۱")),
                ("feature_2_icon", models.CharField(blank=True, default="", max_length=24, verbose_name="نماد ویژگی ۲")),
                ("feature_2_number", models.CharField(blank=True, default="", max_length=8, verbose_name="شمارهٔ ویژگی ۲")),
                ("feature_2_title", models.CharField(blank=True, default="", max_length=140, verbose_name="عنوان ویژگی ۲")),
                ("feature_2_description", models.TextField(blank=True, default="", verbose_name="توضیح ویژگی ۲")),
                ("feature_2_link_label", models.CharField(blank=True, default="", max_length=100, verbose_name="متن پیوند ویژگی ۲")),
                ("feature_2_link_url", models.CharField(blank=True, default="", max_length=500, validators=[portal.models.validate_cms_link], verbose_name="پیوند ویژگی ۲")),
                ("feature_3_icon", models.CharField(blank=True, default="", max_length=24, verbose_name="نماد ویژگی ۳")),
                ("feature_3_number", models.CharField(blank=True, default="", max_length=8, verbose_name="شمارهٔ ویژگی ۳")),
                ("feature_3_title", models.CharField(blank=True, default="", max_length=140, verbose_name="عنوان ویژگی ۳")),
                ("feature_3_description", models.TextField(blank=True, default="", verbose_name="توضیح ویژگی ۳")),
                ("feature_3_link_label", models.CharField(blank=True, default="", max_length=100, verbose_name="متن پیوند ویژگی ۳")),
                ("feature_3_link_url", models.CharField(blank=True, default="", max_length=500, validators=[portal.models.validate_cms_link], verbose_name="پیوند ویژگی ۳")),
                ("legacy_source", models.TextField(blank=True, default="", editable=False, verbose_name="نسخهٔ پشتیبان محتوای قبلی")),
            ],
            options={"verbose_name": "کارت‌های امکانات", "verbose_name_plural": "کارت‌های امکانات"},
            bases=("cms.cmsplugin",),
        ),
        migrations.CreateModel(
            name="CMSFAQList",
            fields=[
                ("cmsplugin_ptr", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    parent_link=True,
                    primary_key=True,
                    related_name="portal_faq_list",
                    to="cms.cmsplugin",
                )),
                ("question_1", models.CharField(blank=True, default="", max_length=240, verbose_name="پرسش ۱")),
                ("answer_1", models.TextField(blank=True, default="", verbose_name="پاسخ ۱")),
                ("question_2", models.CharField(blank=True, default="", max_length=240, verbose_name="پرسش ۲")),
                ("answer_2", models.TextField(blank=True, default="", verbose_name="پاسخ ۲")),
                ("question_3", models.CharField(blank=True, default="", max_length=240, verbose_name="پرسش ۳")),
                ("answer_3", models.TextField(blank=True, default="", verbose_name="پاسخ ۳")),
                ("legacy_source", models.TextField(blank=True, default="", editable=False, verbose_name="نسخهٔ پشتیبان محتوای قبلی")),
            ],
            options={"verbose_name": "پرسش‌های متداول", "verbose_name_plural": "پرسش‌های متداول"},
            bases=("cms.cmsplugin",),
        ),
    ]
