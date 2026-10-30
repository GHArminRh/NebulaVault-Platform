from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.db import transaction

from cms.api import add_plugin, create_page
from cms.models import PageContent, PageUrl, Placeholder
from cms.models.pluginmodel import CMSPlugin
from cms.utils.placeholder import rescan_placeholders_for_obj


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
                    published=True,
                    site=site,
                    page_title="نبیولا والت — یک فضای یکپارچه برای دنیای دیجیتال شما",
                    meta_description="محصولات، تعرفه‌ها، نسخه‌ها و محتوای نبیولا والت را از یک فضای امن و یکپارچه ببینید.",
                )
                created_page = True

        seeded = []
        with transaction.atomic():
            page.set_as_homepage()

            page_content = PageContent.objects.filter(page=page, language="fa").first()
            if page_content is None:
                self.stdout.write(self.style.ERROR(
                    "CMS homepage bootstrap skipped: the Persian page content does not exist."
                ))
                return

            # Remember which slots already existed before changing the template.
            # An empty old slot may mean that an editor intentionally removed its
            # plugin; startup must not silently recreate it on every deployment.
            existing_slots = set(
                Placeholder.objects.get_for_obj(page_content).values_list("slot", flat=True)
            )

            if page_content.template != "portal/cms_home_page.html":
                page_content.template = "portal/cms_home_page.html"
                page_content.save(update_fields=["template"])

            placeholders = rescan_placeholders_for_obj(page_content)
            required = {
                "hero", "content", "products", "pricing",
                "features", "releases", "blog", "about",
            }
            missing = required.difference(placeholders)
            if missing:
                self.stdout.write(self.style.ERROR(
                    "CMS homepage template is missing placeholders: " + ", ".join(sorted(missing))
                ))
                return

            # Seed defaults only for a brand-new homepage or placeholders first
            # introduced by a template update. Never move, rewrite, or delete
            # existing plugin rows: those belong to the site editor.
            defaults = {
                "hero": ("TextPlugin", {"body": HERO_COPY}),
                "features": ("TextPlugin", {"body": FEATURE_GRID}),
                "about": ("TextPlugin", {"body": FAQ_CONTENT}),
                "products": ("LiveProductGridPlugin", {}),
                "pricing": ("LivePricingGridPlugin", {}),
                "releases": ("LiveReleaseListPlugin", {}),
                "blog": ("LiveBlogListPlugin", {}),
            }

            for slot, (plugin_type, values) in defaults.items():
                is_new_slot = slot not in existing_slots
                if not (created_page or is_new_slot):
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

        self.stdout.write(self.style.SUCCESS(
            f"CMS homepage {page.pk} is ready. "
            f"Seeded new regions: {', '.join(seeded) or 'none'}; "
            "existing CMS content was left untouched."
        ))
