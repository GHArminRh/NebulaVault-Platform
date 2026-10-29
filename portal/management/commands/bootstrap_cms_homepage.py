from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site

from cms.api import add_plugin, create_page
from cms.models import PageUrl


class Command(BaseCommand):
    help = "Create the initial editable Persian CMS homepage if none exists."

    def handle(self, *args, **options):
        site = Site.objects.get(pk=settings.SITE_ID)
        existing_home = PageUrl.objects.filter(
            site=site,
            language="fa",
            path__in=("", "/"),
        ).select_related("page").first()
        if existing_home:
            self.stdout.write(
                self.style.WARNING(
                    f"CMS homepage already exists (page id {existing_home.page_id}); leaving it unchanged."
                )
            )
            return

        page = create_page(
            title="خانه",
            template="portal/cms_home_page.html",
            language="fa",
            slug="home",
            created_by="bootstrap_cms_homepage",
            in_navigation=True,
            published=True,
            is_home=True,
            site=site,
            page_title="نبیولا والت — یک فضای یکپارچه برای دنیای دیجیتال شما",
            meta_description="محصولات، تعرفه‌ها، نسخه‌ها و محتوای نبیولا والت را در یک فضای امن و یکپارچه ببینید.",
        )
        placeholder = page.get_placeholders(language="fa").get(slot="content")

        # Editable copy is stored in CMS text plugins. Live catalogue plugins
        # continue to read products, plans, releases, and published blog posts
        # from their existing application models.
        add_plugin(
            placeholder,
            "TextPlugin",
            "fa",
            body=(
                '<section class="nv-home-hero page-wrap" id="home">'
                '<div class="nv-hero-copy">'
                '<div class="eyebrow"><i class="pulse"></i> فضای دیجیتال شما، با نظم تازه</div>'
                '<h1>همه‌چیز سر جای خودش؛<br><span class="gradient-text">کنترل در دست شما.</span></h1>'
                '<p class="hero-lede">محصولات، خریدها، اشتراک‌ها و لایسنس‌ها را در یک تجربهٔ امن و هماهنگ مدیریت کنید؛ ساده، شفاف و بدون شلوغی.</p>'
                '<div class="hero-actions"><a class="button button-primary button-large" href="#products">کشف محصولات ↙</a>'
                '<a class="button button-glass button-large" href="/dashboard/">ورود به فضای من ↗</a></div>'
                '<div class="nv-hero-trust"><span><i class="pulse"></i> حساب شخصی امن</span><span>◇ خرید و لایسنس یکپارچه</span><span>⌁ تجربهٔ هماهنگ</span></div>'
                '</div><div class="nv-hero-visual" aria-label="فضای امن نبیولا والت"><div class="nv-visual-halo"></div>'
                '<div class="nv-visual-orbit nv-orbit-one"></div><div class="nv-visual-orbit nv-orbit-two"></div>'
                '<div class="nv-visual-orbit nv-orbit-three"></div><div class="nv-visual-core"><div class="nv-core-inner">◇</div>'
                '<span class="nv-core-caption">NEBULA VAULT</span></div><div class="nv-float-card nv-float-top"><span class="nv-float-icon">⌑</span>'
                '<span><strong>فضای محافظت‌شده</strong><small>حساب شما، در یک نگاه</small></span><i class="pulse"></i></div>'
                '<div class="nv-float-card nv-float-bottom"><span class="nv-float-icon">✦</span><span><strong>همه‌چیز هماهنگ</strong><small>محصول · خرید · لایسنس</small></span></div>'
                '<span class="nv-visual-star nv-star-one">✦</span><span class="nv-visual-star nv-star-two">✧</span></div>'
                '<a class="nv-scroll-cue" href="#products"><span></span> برای کشف بیشتر اسکرول کنید</a></section>'
                '<section class="nv-proof-strip"><div class="page-wrap nv-proof-inner"><span>یک تجربهٔ یکپارچه</span>'
                '<span><b>01</b> انتخاب محصول</span><span><b>02</b> خرید شفاف</span><span><b>03</b> مدیریت لایسنس</span>'
                '<span><b>04</b> کنترل از پیشخوان</span></div></section>'
            ),
        )
        add_plugin(placeholder, "LiveProductGridPlugin", "fa")
        add_plugin(placeholder, "LivePricingGridPlugin", "fa")
        add_plugin(
            placeholder,
            "TextPlugin",
            "fa",
            body=(
                '<section class="section page-wrap nv-home-section" id="features"><div class="section-heading"><div>'
                '<div class="eyebrow">طراحی حول محور شما</div><h2>یک حساب. همهٔ ابزارهای مهم.</h2>'
                '<p>تجربه‌ای که از صفحهٔ اصلی تا پیشخوان کاربر، یک زبان بصری دارد.</p></div>'
                '<span class="nv-section-index">03 / EXPERIENCE</span></div><div class="nv-feature-grid">'
                '<article class="nv-feature-card nv-feature-highlight"><span class="nv-feature-icon">⌘</span><span class="nv-feature-number">01</span>'
                '<h3>پیشخوان متمرکز</h3><p>اشتراک‌های فعال، سفارش‌های اخیر، وضعیت لایسنس‌ها و تنظیمات حساب در یک فضای مشخص.</p>'
                '<a href="/dashboard/">رفتن به فضای کار ↗</a></article>'
                '<article class="nv-feature-card"><span class="nv-feature-icon">◇</span><span class="nv-feature-number">02</span>'
                '<h3>خرید شفاف</h3><p>طرح‌ها، مدت اعتبار و مبلغ را پیش از ادامهٔ خرید بررسی کنید.</p>'
                '<a href="#pricing">دیدن طرح‌ها ↙</a></article>'
                '<article class="nv-feature-card"><span class="nv-feature-icon">⌑</span><span class="nv-feature-number">03</span>'
                '<h3>مدیریت دسترسی</h3><p>اطلاعات لایسنس و وضعیت اشتراک‌ها را در فضای حساب خود دنبال کنید.</p>'
                '<a href="/dashboard/#my-licenses">لایسنس‌های من ↗</a></article></div></section>'
            ),
        )
        add_plugin(placeholder, "LiveBlogListPlugin", "fa")
        add_plugin(placeholder, "LiveReleaseListPlugin", "fa")
        add_plugin(
            placeholder,
            "TextPlugin",
            "fa",
            body=(
                '<section class="section page-wrap nv-home-section nv-faq-section" id="about">'
                '<div class="section-heading"><div><div class="eyebrow">پرسش‌های رایج</div><h2>شروعی ساده و روشن.</h2>'
                '<p>چند پاسخ کوتاه برای شروع کار با نبیولا والت.</p></div><span class="nv-section-index">05 / FAQ</span></div>'
                '<div class="nv-faq-list"><details><summary>چطور خریدها و لایسنس‌هایم را ببینم؟<span>＋</span></summary>'
                '<p>پس از ورود به حساب، از پیشخوان می‌توانید سفارش‌ها، اشتراک‌ها و لایسنس‌های مرتبط با حساب خود را مشاهده کنید.</p></details>'
                '<details><summary>برای ساخت حساب چه کاری لازم است؟<span>＋</span></summary>'
                '<p>با ایمیل و رمز عبور ثبت‌نام کنید و نشانی ایمیل خود را از طریق پیوند یا کد تأیید ارسال‌شده فعال کنید.</p></details>'
                '<details><summary>آیا برای دیدن طرح‌ها باید وارد حساب شوم؟<span>＋</span></summary>'
                '<p>خیر؛ می‌توانید محصولات و طرح‌ها را بررسی کنید. برای مدیریت خریدها و دسترسی‌های شخصی، ورود به حساب لازم است.</p></details></div></section>'
                '<section class="closing-cta page-wrap nv-final-cta"><div class="eyebrow"><i class="pulse"></i> فضای شما آماده است</div>'
                '<h2>تجربهٔ یکپارچه را شروع کنید.</h2><p>یک حساب بسازید و ابزارهای دیجیتال خود را با نظم بیشتری مدیریت کنید.</p>'
                '<a class="button button-primary button-large" href="/accounts/register/">ایجاد حساب کاربری ↗</a></section>'
            ),
        )
        self.stdout.write(self.style.SUCCESS(
            f"Created editable Persian CMS homepage (page id {page.pk})."
        ))
