"""Create and safely normalize the editable Persian django CMS homepage.

The command is idempotent: it preserves unrelated editor content and migrates
only the known seed plugins created by older versions of this command.
"""
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.db import transaction

from cms.api import add_plugin, create_page
from cms.models import PageContent, PageUrl
from cms.models.pluginmodel import CMSPlugin


HERO_COPY = """
<div class="eyebrow"><i class="pulse"></i> فضای دیجیتال شما، با نظم تازه</div>
<h1>همه‌چیز سر جای خودش؛<br><span class="gradient-text">کنترل در دست شما.</span></h1>
<p class="hero-lede">محصولات، خریدها، اشتراک‌ها و لایسنس‌ها را در یک تجربهٔ امن و هماهنگ مدیریت کنید؛ ساده، شفاف و بدون شلوغی.</p>
<div class="hero-actions">
  <a class="button button-primary button-large" href="/products/">کشف محصولات ↙</a>
  <a class="button button-glass button-large" href="/pricing/">مشاهده تعرفه‌ها ↗</a>
</div>
<div class="nv-hero-trust"><span><i class="pulse"></i> حساب شخصی امن</span><span>◇ خرید و لایسنس یکپارچه</span><span>⌁ تجربهٔ هماهنگ</span></div>
"""

FEATURE_GRID = """
<div class="nv-feature-grid">
  <article class="nv-feature-card nv-feature-highlight"><span class="nv-feature-icon">⌘</span><span class="nv-feature-number">01</span><h3>پیشخوان متمرکز</h3><p>اشتراک‌های فعال، سفارش‌های اخیر، وضعیت لایسنس‌ها و تنظیمات حساب در یک فضای مشخص.</p><a href="/dashboard/">رفتن به فضای کار ↗</a></article>
  <article class="nv-feature-card"><span class="nv-feature-icon">◇</span><span class="nv-feature-number">02</span><h3>خرید شفاف</h3><p>طرح‌ها، مدت اعتبار و مبلغ را پیش از ادامهٔ خرید بررسی کنید.</p><a href="/pricing/">دیدن طرح‌ها ↙</a></article>
  <article class="nv-feature-card"><span class="nv-feature-icon">⌑</span><span class="nv-feature-number">03</span><h3>مدیریت دسترسی</h3><p>اطلاعات لایسنس و وضعیت اشتراک‌ها را در فضای حساب خود دنبال کنید.</p><a href="/dashboard/">لایسنس‌های من ↗</a></article>
</div>
"""

FAQ_CONTENT = """
<div class="nv-faq-list">
  <details><summary>چطور خریدها و لایسنس‌هایم را ببینم؟<span>＋</span></summary><p>پس از ورود به حساب، از پیشخوان می‌توانید سفارش‌ها، اشتراک‌ها و لایسنس‌های مرتبط با حساب خود را مشاهده کنید.</p></details>
  <details><summary>برای ساخت حساب چه کاری لازم است؟<span>＋</span></summary><p>با ایمیل و رمز عبور ثبت‌نام کنید و نشانی ایمیل خود را از طریق پیوند یا کد تأیید ارسال‌شده فعال کنید.</p></details>
  <details><summary>آیا برای دیدن طرح‌ها باید وارد حساب شوم؟<span>＋</span></summary><p>خیر؛ می‌توانید محصولات و طرح‌ها را بررسی کنید. برای مدیریت خریدها و دسترسی‌های شخصی، ورود به حساب لازم است.</p></details>
</div>
"""


class Command(BaseCommand):
    help = "Create or safely complete the editable Persian CMS homepage."

    def handle(self, *args, **options):
        site = Site.objects.filter(pk=settings.SITE_ID).first()
        if site is None:
            self.stdout.write(self.style.WARNING(
                "CMS homepage bootstrap skipped: the configured Django Site does not exist."
            ))
            return

        root_url = PageUrl.objects.filter(
            site=site, language="fa", path__in=("", "/")
        ).select_related("page").first()

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
                    published=True,
                    site=site,
                    page_title="نبیولا والت — یک فضای یکپارچه برای دنیای دیجیتال شما",
                    meta_description="محصولات، تعرفه‌ها، نسخه‌ها و محتوای نبیولا والت را از یک فضای امن و یکپارچه ببینید.",
                )

        with transaction.atomic():
            page.set_as_homepage()

            page_content = PageContent.objects.filter(page=page, language="fa").first()
            if page_content and page_content.template != "portal/cms_home_page.html":
                page_content.template = "portal/cms_home_page.html"
                page_content.save(update_fields=["template"])

            placeholders = {
                item.slot: item for item in page.get_placeholders(language="fa")
            }
            required = {"hero", "content", "products", "pricing", "features", "releases", "blog", "about"}
            missing = required.difference(placeholders)
            if missing:
                self.stdout.write(self.style.ERROR(
                    "CMS homepage template is missing placeholders: " + ", ".join(sorted(missing))
                ))
                return

            # Move only recognizable plugins created by the previous bootstrap.
            # Unknown/user-authored plugins in the general content region remain untouched.
            content_placeholder = placeholders["content"]
            migrated = []
            legacy_destinations = {
                "LiveProductGridPlugin": "products",
                "LivePricingGridPlugin": "pricing",
                "LiveReleaseListPlugin": "releases",
            }
            for plugin in list(
                CMSPlugin.objects.filter(
                    placeholder=content_placeholder, language="fa", parent__isnull=True
                ).order_by("position", "pk")
            ):
                target_slot = legacy_destinations.get(plugin.plugin_type)
                instance = None
                if plugin.plugin_type == "TextPlugin":
                    try:
                        instance, _plugin_class = plugin.get_plugin_instance()
                    except (AttributeError, LookupError, TypeError):
                        instance = None
                    body = getattr(instance, "body", "") if instance else ""
                    if isinstance(body, str) and ('id="home"' in body or "id='home'" in body):
                        target_slot = "hero"
                        instance.body = HERO_COPY
                    elif isinstance(body, str) and ('id="features"' in body or "id='features'" in body):
                        target_slot = "features"
                        instance.body = FEATURE_GRID
                    elif isinstance(body, str) and ('id="about"' in body or "id='about'" in body):
                        target_slot = "about"
                        instance.body = FAQ_CONTENT

                if not target_slot:
                    continue
                target = placeholders[target_slot]
                if instance is not None and target_slot in {"hero", "features", "about"}:
                    instance.save(update_fields=["body"])
                target_position = target.get_next_plugin_position("fa", insert_order="last")
                content_placeholder.move_plugin(
                    plugin, target_position, target_placeholder=target
                )
                migrated.append(target_slot)

            # Fill only empty regions. Existing content is never replaced.
            defaults = {
                "hero": ("TextPlugin", {"body": HERO_COPY}),
                "features": ("TextPlugin", {"body": FEATURE_GRID}),
                "about": ("TextPlugin", {"body": FAQ_CONTENT}),
                "products": ("LiveProductGridPlugin", {}),
                "pricing": ("LivePricingGridPlugin", {}),
                "releases": ("LiveReleaseListPlugin", {}),
                "blog": ("LiveBlogListPlugin", {}),
            }
            created = []
            for slot, (plugin_type, values) in defaults.items():
                target = placeholders[slot]
                if not target.has_plugins(language="fa"):
                    add_plugin(target, plugin_type, "fa", **values)
                    created.append(slot)

        self.stdout.write(self.style.SUCCESS(
            f"CMS homepage {page.pk} is ready. Migrated: {', '.join(migrated) or 'none'}; "
            f"seeded empty regions: {', '.join(created) or 'none'}."
        ))
