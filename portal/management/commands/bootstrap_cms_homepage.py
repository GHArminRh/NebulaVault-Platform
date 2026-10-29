from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.db import transaction

from cms.api import add_plugin, create_page
from cms.models import PageContent, PageUrl
from cms.models.pluginmodel import CMSPlugin


HERO_HTML = """
<section class="nv-home-hero page-wrap" id="home">
  <div class="nv-hero-copy">
    <div class="eyebrow"><i class="pulse"></i> فضای دیجیتال شما، با نظم تازه</div>
    <h1>همه‌چیز سر جای خودش؛<br><span class="gradient-text">کنترل در دست شما.</span></h1>
    <p class="hero-lede">محصولات، خریدها، اشتراک‌ها و لایسنس‌ها را در یک تجربهٔ امن و هماهنگ مدیریت کنید؛ ساده، شفاف و بدون شلوغی.</p>
    <div class="hero-actions"><a class="button button-primary button-large" href="#products">کشف محصولات ↙</a><a class="button button-glass button-large" href="/dashboard/">ورود به فضای من ↗</a></div>
    <div class="nv-hero-trust"><span><i class="pulse"></i> حساب شخصی امن</span><span>◇ خرید و لایسنس یکپارچه</span><span>⌁ تجربهٔ هماهنگ</span></div>
  </div>
  <div class="nv-hero-visual" aria-label="فضای امن نبیولا والت"><div class="nv-visual-halo"></div>
    <div class="nv-visual-orbit nv-orbit-one"></div><div class="nv-visual-orbit nv-orbit-two"></div><div class="nv-visual-orbit nv-orbit-three"></div>
    <div class="nv-visual-core"><div class="nv-core-inner">◇</div><span class="nv-core-caption">NEBULA VAULT</span></div>
    <div class="nv-float-card nv-float-top"><span class="nv-float-icon">⌑</span><span><strong>فضای محافظت‌شده</strong><small>حساب شما، در یک نگاه</small></span><i class="pulse"></i></div>
    <div class="nv-float-card nv-float-bottom"><span class="nv-float-icon">✦</span><span><strong>همه‌چیز هماهنگ</strong><small>محصول · خرید · لایسنس</small></span></div>
    <span class="nv-visual-star nv-star-one">✦</span><span class="nv-visual-star nv-star-two">✧</span>
  </div>
  <a class="nv-scroll-cue" href="#products"><span></span> برای کشف بیشتر اسکرول کنید</a>
</section>
<section class="nv-proof-strip"><div class="page-wrap nv-proof-inner"><span>یک تجربهٔ یکپارچه</span><span><b>01</b> انتخاب محصول</span><span><b>02</b> خرید شفاف</span><span><b>03</b> مدیریت لایسنس</span><span><b>04</b> کنترل از پیشخوان</span></div></section>
"""

FEATURES_HTML = """
<section class="section page-wrap nv-home-section" id="features">
  <div class="section-heading"><div><div class="eyebrow">طراحی حول محور شما</div><h2>یک حساب. همهٔ ابزارهای مهم.</h2><p>تجربه‌ای که از صفحهٔ اصلی تا پیشخوان کاربر، یک زبان بصری دارد.</p></div><span class="nv-section-index">03 / EXPERIENCE</span></div>
  <div class="nv-feature-grid">
    <article class="nv-feature-card nv-feature-highlight"><span class="nv-feature-icon">⌘</span><span class="nv-feature-number">01</span><h3>پیشخوان متمرکز</h3><p>اشتراک‌های فعال، سفارش‌های اخیر، وضعیت لایسنس‌ها و تنظیمات حساب در یک فضای مشخص.</p><a href="/dashboard/">رفتن به فضای کار ↗</a></article>
    <article class="nv-feature-card"><span class="nv-feature-icon">◇</span><span class="nv-feature-number">02</span><h3>خرید شفاف</h3><p>طرح‌ها، مدت اعتبار و مبلغ را پیش از ادامهٔ خرید بررسی کنید.</p><a href="#pricing">دیدن طرح‌ها ↙</a></article>
    <article class="nv-feature-card"><span class="nv-feature-icon">⌑</span><span class="nv-feature-number">03</span><h3>مدیریت دسترسی</h3><p>اطلاعات لایسنس و وضعیت اشتراک‌ها را در فضای حساب خود دنبال کنید.</p><a href="/dashboard/#my-licenses">لایسنس‌های من ↗</a></article>
  </div>
</section>
"""

FAQ_HTML = """
<section class="section page-wrap nv-home-section nv-faq-section" id="about">
  <div class="section-heading"><div><div class="eyebrow">پرسش‌های رایج</div><h2>شروعی ساده و روشن.</h2><p>چند پاسخ کوتاه برای شروع کار با نبیولا والت.</p></div><span class="nv-section-index">05 / FAQ</span></div>
  <div class="nv-faq-list">
    <details><summary>چطور خریدها و لایسنس‌هایم را ببینم؟<span>＋</span></summary><p>پس از ورود به حساب، از پیشخوان می‌توانید سفارش‌ها، اشتراک‌ها و لایسنس‌های مرتبط با حساب خود را مشاهده کنید.</p></details>
    <details><summary>برای ساخت حساب چه کاری لازم است؟<span>＋</span></summary><p>با ایمیل و رمز عبور ثبت‌نام کنید و نشانی ایمیل خود را از طریق پیوند یا کد تأیید ارسال‌شده فعال کنید.</p></details>
    <details><summary>آیا برای دیدن طرح‌ها باید وارد حساب شوم؟<span>＋</span></summary><p>خیر؛ می‌توانید محصولات و طرح‌ها را بررسی کنید. برای مدیریت خریدها و دسترسی‌های شخصی، ورود به حساب لازم است.</p></details>
  </div>
</section>
<section class="closing-cta page-wrap nv-final-cta"><div class="eyebrow"><i class="pulse"></i> فضای شما آماده است</div><h2>تجربهٔ یکپارچه را شروع کنید.</h2><p>یک حساب بسازید و ابزارهای دیجیتال خود را با نظم بیشتری مدیریت کنید.</p><a class="button button-primary button-large" href="/accounts/register/">ایجاد حساب کاربری ↗</a></section>
"""


class Command(BaseCommand):
    help = "Create or safely complete the editable Persian CMS homepage."

    def handle(self, *args, **options):
        site = Site.objects.filter(pk=settings.SITE_ID).first()
        if site is None:
            self.stdout.write(self.style.WARNING(
                "CMS homepage bootstrap skipped because the configured Django Site does not exist yet."
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

        placeholder = page.get_placeholders(language="fa").filter(slot="content").first()
        if placeholder is None:
            self.stdout.write(self.style.ERROR(
                f"CMS homepage page {page.pk} has no content placeholder; no plugins were changed."
            ))
            return

        existing_plugins = list(
            CMSPlugin.objects.filter(placeholder=placeholder, language="fa").order_by("position", "pk")
        )
        existing_types = {plugin.plugin_type for plugin in existing_plugins}
        text_bodies = []
        for plugin in existing_plugins:
            try:
                instance, _plugin_class = plugin.get_plugin_instance()
            except (AttributeError, LookupError, TypeError):
                instance = None
            body = getattr(instance, "body", "")
            if isinstance(body, str):
                text_bodies.append(body)

        created = []
        # Only seed the structural sections that are absent. Existing editorial
        # text and any live plugins are kept, making this command safe on restarts.
        if not any('id="home"' in body or "id='home'" in body for body in text_bodies):
            add_plugin(placeholder, "TextPlugin", "fa", body=HERO_HTML, position="first")
            created.append("hero")

        live_plugins = (
            ("LiveProductGridPlugin", "products"),
            ("LivePricingGridPlugin", "pricing"),
        )
        for plugin_type, label in live_plugins:
            if plugin_type not in existing_types:
                add_plugin(placeholder, plugin_type, "fa")
                created.append(label)

        if not any('id="features"' in body or "id='features'" in body for body in text_bodies):
            add_plugin(placeholder, "TextPlugin", "fa", body=FEATURES_HTML)
            created.append("features")

        for plugin_type, label in (
            ("LiveBlogListPlugin", "blog"),
            ("LiveReleaseListPlugin", "releases"),
        ):
            if plugin_type not in existing_types:
                add_plugin(placeholder, plugin_type, "fa")
                created.append(label)

        if not any('id="about"' in body or "id='about'" in body for body in text_bodies):
            add_plugin(placeholder, "TextPlugin", "fa", body=FAQ_HTML)
            created.append("faq")

        if created:
            self.stdout.write(self.style.SUCCESS(
                f"CMS homepage {page.pk} completed; added missing sections: {', '.join(created)}."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"CMS homepage {page.pk} is already complete; no changes needed."
            ))
