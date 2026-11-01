import django.core.validators
import django.db.models.deletion
from django.db import migrations, models
import wagtail.fields


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("wagtailcore", "0098_apitoken"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomePage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
                (
                    "hero_eyebrow",
                    models.CharField(
                        default="فضای دیجیتال شما، با نظم تازه",
                        max_length=120,
                        verbose_name="متن بالای عنوان",
                    ),
                ),
                (
                    "hero_title",
                    models.CharField(
                        default="همه‌چیز سر جای خودش؛",
                        max_length=180,
                        verbose_name="عنوان اصلی",
                    ),
                ),
                (
                    "hero_highlight",
                    models.CharField(
                        default="کنترل در دست شما.",
                        max_length=180,
                        verbose_name="عنوان تأکیدی",
                    ),
                ),
                (
                    "hero_description",
                    models.CharField(
                        default=(
                            "محصولات، خریدها، اشتراک‌ها و لایسنس‌ها را در یک تجربه‌ی امن "
                            "و هماهنگ مدیریت کنید؛ ساده، شفاف و بدون شلوغی."
                        ),
                        max_length=500,
                        verbose_name="توضیحات معرفی",
                    ),
                ),
                (
                    "hero_primary_cta_label",
                    models.CharField(
                        default="کشف محصولات",
                        max_length=80,
                        verbose_name="متن دکمه اصلی",
                    ),
                ),
                (
                    "hero_primary_cta_url",
                    models.CharField(
                        default="#products",
                        max_length=300,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="از نشانی داخلی، لنگر صفحه یا پیوند HTTPS استفاده کنید.",
                                regex=r"^(?:#|/(?!/)|https://)\S*$",
                            )
                        ],
                        verbose_name="پیوند دکمه اصلی",
                    ),
                ),
                (
                    "body",
                    wagtail.fields.RichTextField(
                        blank=True,
                        features=[
                            "h2", "h3", "bold", "italic", "link", "ul", "ol",
                            "blockquote", "hr", "image", "document-link",
                        ],
                        verbose_name="محتوای تکمیلی صفحه اصلی",
                    ),
                ),
            ],
            options={
                "verbose_name": "صفحه اصلی",
                "verbose_name_plural": "صفحه اصلی",
            },
            bases=("wagtailcore.page",),
        ),
        migrations.CreateModel(
            name="ContentPage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
                (
                    "intro",
                    models.CharField(
                        blank=True,
                        max_length=500,
                        verbose_name="معرفی کوتاه",
                    ),
                ),
                (
                    "body",
                    wagtail.fields.RichTextField(
                        blank=True,
                        features=[
                            "h2", "h3", "h4", "bold", "italic", "link", "ul", "ol",
                            "blockquote", "hr", "image", "document-link", "embed",
                        ],
                        verbose_name="محتوای صفحه",
                    ),
                ),
            ],
            options={
                "verbose_name": "صفحه محتوایی",
                "verbose_name_plural": "صفحات محتوایی",
            },
            bases=("wagtailcore.page",),
        ),
    ]
