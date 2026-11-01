import uuid

import sitecms.blocks
import wagtail.fields
from django.db import migrations


def seed_homepage_sections(apps, schema_editor):
    HomePage = apps.get_model("sitecms", "HomePage")
    alias = schema_editor.connection.alias
    homepage = HomePage.objects.using(alias).filter(slug="home").first()
    if homepage is None:
        return

    sections = list(homepage.sections or [])
    existing = {item.get("type") for item in sections if isinstance(item, dict)}

    defaults = [
        (
            "proof_strip",
            {
                "title": "یک تجربه‌ی یکپارچه",
                "items": [
                    {"number": "01", "label": "انتخاب محصول"},
                    {"number": "02", "label": "خرید شفاف"},
                    {"number": "03", "label": "مدیریت لایسنس"},
                    {"number": "04", "label": "کنترل از پیشخوان"},
                ],
            },
        ),
        (
            "feature_grid",
            {
                "eyebrow": "طراحی حول محور شما",
                "title": "یک حساب. همه‌ی ابزارهای مهم.",
                "description": "تجربه‌ای که از صفحه‌ی اصلی تا پیشخوان کاربر، یک زبان بصری دارد.",
                "items": [
                    {
                        "icon": "⌘",
                        "title": "پیشخوان متمرکز",
                        "text": "اشتراک‌های فعال، سفارش‌های اخیر، وضعیت لایسنس‌ها و تنظیمات حساب در یک فضای مشخص.",
                        "link_label": "رفتن به فضای کار",
                        "link_url": "/dashboard/",
                    },
                    {
                        "icon": "◇",
                        "title": "انتخاب آگاهانه",
                        "text": "جزئیات و طرح‌های هر محصول را در صفحه‌ی اختصاصی همان محصول بررسی کنید.",
                        "link_label": "مشاهده محصولات",
                        "link_url": "#products",
                    },
                    {
                        "icon": "⌑",
                        "title": "مدیریت دسترسی",
                        "text": "اطلاعات لایسنس و وضعیت اشتراک‌ها را در فضای حساب خود دنبال کنید.",
                        "link_label": "لایسنس‌های من",
                        "link_url": "/dashboard/#my-licenses",
                    },
                ],
            },
        ),
        (
            "faq",
            {
                "eyebrow": "پرسش‌های رایج",
                "title": "شروعی ساده و روشن.",
                "description": "چند پاسخ کوتاه برای شروع کار با نبیولا والت.",
                "items": [
                    {
                        "question": "چطور خریدها و لایسنس‌هایم را ببینم؟",
                        "answer": "پس از ورود به حساب، از پیشخوان می‌توانید سفارش‌ها، اشتراک‌ها و لایسنس‌های مرتبط با حساب خود را مشاهده کنید.",
                    },
                    {
                        "question": "برای ساخت حساب چه کاری لازم است؟",
                        "answer": "با ایمیل و رمز عبور ثبت‌نام کنید و نشانی ایمیل خود را از طریق پیوند یا کد تأیید ارسال‌شده فعال کنید.",
                    },
                    {
                        "question": "آیا برای دیدن طرح‌ها باید وارد حساب شوم؟",
                        "answer": "خیر؛ می‌توانید محصولات و طرح‌ها را بررسی کنید. برای مدیریت خریدها و دسترسی‌های شخصی، ورود به حساب لازم است.",
                    },
                ],
            },
        ),
        (
            "call_to_action",
            {
                "eyebrow": "فضای شما آماده است",
                "title": "تجربه‌ی یکپارچه را شروع کنید.",
                "text": "یک حساب بسازید و ابزارهای دیجیتال خود را با نظم بیشتری مدیریت کنید.",
                "button_label": "ایجاد حساب کاربری",
                "button_url": "/accounts/register/",
            },
        ),
    ]

    for block_type, value in defaults:
        if block_type not in existing:
            sections.append(
                {"type": block_type, "value": value, "id": str(uuid.uuid4())}
            )

    HomePage.objects.using(alias).filter(pk=homepage.pk).update(sections=sections)


class Migration(migrations.Migration):
    dependencies = [
        ("sitecms", "0003_streamfield_sections"),
    ]

    operations = [
        migrations.AlterField(
            model_name="homepage",
            name="sections",
            field=wagtail.fields.StreamField(
                sitecms.blocks.NebulaContentBlock(),
                blank=True,
                use_json_field=True,
                verbose_name="بخش‌های قابل چیدمان صفحه اصلی",
            ),
        ),
        migrations.AlterField(
            model_name="contentpage",
            name="sections",
            field=wagtail.fields.StreamField(
                sitecms.blocks.NebulaContentBlock(),
                blank=True,
                use_json_field=True,
                verbose_name="بخش‌های محتوایی صفحه",
            ),
        ),
        migrations.RunPython(seed_homepage_sections, migrations.RunPython.noop),
    ]
