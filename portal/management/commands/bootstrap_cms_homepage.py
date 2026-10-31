from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cms.api import add_plugin, create_page
from cms.models import PageContent, PageUrl, Placeholder
from cms.models.pluginmodel import CMSPlugin
from cms.utils.placeholder import rescan_placeholders_for_obj

from portal.cms_legacy import convert_legacy_homepage_sections


HERO_DEFAULTS = {
    "eyebrow": "فضای دیجیتال شما، با نظم تازه",
    "heading": "همه‌چیز سر جای خودش؛",
    "heading_accent": "کنترل در دست شما.",
    "description": "محصولات، خریدها، اشتراک‌ها و لایسنس‌ها را در یک تجربهٔ امن و هماهنگ مدیریت کنید؛ ساده، شفاف و بدون شلوغی.",
    "primary_cta_label": "کشف محصولات ↙",
    "primary_cta_url": "/products/",
    "secondary_cta_label": "مشاهده تعرفه‌ها ↗",
    "secondary_cta_url": "/pricing/",
    "trust_item_1": "حساب شخصی امن",
    "trust_item_2": "خرید و لایسنس یکپارچه",
    "trust_item_3": "تجربهٔ هماهنگ",
}

FEATURE_DEFAULTS = {
    "feature_1_icon": "⌘",
    "feature_1_number": "01",
    "feature_1_title": "پیشخوان متمرکز",
    "feature_1_description": "اشتراک‌های فعال، سفارش‌های اخیر، وضعیت لایسنس‌ها و تنظیمات حساب در یک فضای مشخص.",
    "feature_1_link_label": "رفتن به فضای کار",
    "feature_1_link_url": "/dashboard/",
    "feature_2_icon": "◇",
    "feature_2_number": "02",
    "feature_2_title": "خرید شفاف",
    "feature_2_description": "طرح‌ها، مدت اعتبار و مبلغ را پیش از ادامهٔ خرید بررسی کنید.",
    "feature_2_link_label": "دیدن طرح‌ها",
    "feature_2_link_url": "/pricing/",
    "feature_3_icon": "⌑",
    "feature_3_number": "03",
    "feature_3_title": "مدیریت دسترسی",
    "feature_3_description": "اطلاعات لایسنس و وضعیت اشتراک‌ها را در فضای حساب خود دنبال کنید.",
    "feature_3_link_label": "لایسنس‌های من",
    "feature_3_link_url": "/dashboard/",
}

FAQ_DEFAULTS = {
    "question_1": "چطور خریدها و لایسنس‌هایم را ببینم؟",
    "answer_1": "پس از ورود به حساب، از پیشخوان می‌توانید سفارش‌ها، اشتراک‌ها و لایسنس‌های مرتبط با حساب خود را مشاهده کنید.",
    "question_2": "برای ساخت حساب چه کاری لازم است؟",
    "answer_2": "با ایمیل و رمز عبور ثبت‌نام کنید و نشانی ایمیل خود را از طریق پیوند یا کد تأیید ارسال‌شده فعال کنید.",
    "question_3": "آیا برای دیدن طرح‌ها باید وارد حساب شوم؟",
    "answer_3": "خیر؛ می‌توانید محصولات و طرح‌ها را بررسی کنید. برای مدیریت خریدها و دسترسی‌های شخصی، ورود به حساب لازم است.",
}


class Command(BaseCommand):
    help = "Create or safely complete the editable Persian CMS homepage."

    def handle(self, *args, **options):
        site = Site.objects.filter(pk=settings.SITE_ID).first()
        if site is None:
            raise CommandError(
                "CMS homepage bootstrap cannot continue: "
                "the configured Django Site does not exist."
            )

        seeded = []
        converted = []
        conversion_errors = []
        with transaction.atomic():
            root_url = PageUrl.objects.filter(
                site=site, language="fa", path__in=("", "/")
            ).select_related("page").first()

            created_page = False
            if root_url:
                page = root_url.page
            else:
                existing_content = PageContent.objects.filter(
                    page__site=site,
                    page__parent__isnull=True,
                    language="fa",
                    slug="home",
                ).select_related("page").first()
                if existing_content:
                    page = existing_content.page
                else:
                    page = create_page(
                        title="خانه",
                        template="portal/cms_home_page.html",
                        language="fa",
                        slug="home",
                        created_by="bootstrap_cms_homepage",
                        in_navigation=True,
                        site=site,
                        page_title="نبیولا والت — یک فضای یکپارچه برای دنیای دیجیتال شما",
                        meta_description="محصولات، تعرفه‌ها، نسخه‌ها و محتوای نبیولا والت را از یک فضای امن و یکپارچه ببینید.",
                    )
                    created_page = True

            page.set_as_homepage()

            page_content = PageContent.objects.filter(page=page, language="fa").first()
            if page_content is None:
                raise CommandError(
                    "CMS homepage bootstrap cannot continue: "
                    "the Persian page content does not exist."
                )

            # A previously empty slot can represent an intentional editor deletion.
            # Only seed a slot when the page or that slot is genuinely new.
            existing_slots = set(
                Placeholder.objects.get_for_obj(page_content).values_list("slot", flat=True)
            )

            if page_content.template != "portal/cms_home_page.html":
                page_content.template = "portal/cms_home_page.html"
                page_content.save(update_fields=["template"])

            placeholders = rescan_placeholders_for_obj(page_content)
            required = {
                "hero", "content", "products",
                "features", "releases", "blog", "about",
            }
            missing = required.difference(placeholders)
            if missing:
                raise CommandError(
                    "CMS homepage template is missing placeholders: "
                    + ", ".join(sorted(missing))
                )

            defaults = {
                "hero": ("HeroContentPlugin", HERO_DEFAULTS),
                "features": ("FeatureGridPlugin", FEATURE_DEFAULTS),
                "about": ("FAQListPlugin", FAQ_DEFAULTS),
                "products": ("LiveProductGridPlugin", {}),
                "releases": ("LiveReleaseListPlugin", {}),
                "blog": ("LiveBlogListPlugin", {}),
            }

            for slot, (plugin_type, values) in defaults.items():
                if not (created_page or slot not in existing_slots):
                    continue

                target = placeholders[slot]
                has_plugins = CMSPlugin.objects.filter(
                    placeholder_id=target.pk,
                    language="fa",
                ).exists()
                if has_plugins:
                    continue

                add_plugin(target, plugin_type, "fa", **values)
                seeded.append(slot)

            # Preserve older hand-authored TextPlugins while replacing only
            # well-known, single-block homepage layouts with structured plugins.
            converted, conversion_errors = convert_legacy_homepage_sections(page_content)

        self.stdout.write(self.style.SUCCESS(
            f"CMS homepage {page.pk} is ready. "
            f"Seeded new regions: {', '.join(seeded) or 'none'}; "
            f"converted legacy regions: {', '.join(slot for slot, _pk in converted) or 'none'}; "
            "existing unsupported or nested editor content was preserved."
        ))
        for slot, error_name in conversion_errors:
            self.stderr.write(self.style.WARNING(
                f"Legacy CMS conversion skipped for '{slot}' ({error_name}); "
                "the original plugin remains intact."
            ))
