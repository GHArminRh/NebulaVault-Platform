from django.core.validators import RegexValidator
from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.search import index


class HomePage(Page):
    """Editable content fields for the existing Nebula Vault storefront homepage."""

    hero_eyebrow = models.CharField(
        max_length=120,
        default="فضای دیجیتال شما، با نظم تازه",
        verbose_name="متن بالای عنوان",
    )
    hero_title = models.CharField(
        max_length=180,
        default="همه‌چیز سر جای خودش؛",
        verbose_name="عنوان اصلی",
    )
    hero_highlight = models.CharField(
        max_length=180,
        default="کنترل در دست شما.",
        verbose_name="عنوان تأکیدی",
    )
    hero_description = models.CharField(
        max_length=500,
        default=(
            "محصولات، خریدها، اشتراک‌ها و لایسنس‌ها را در یک تجربه‌ی امن "
            "و هماهنگ مدیریت کنید؛ ساده، شفاف و بدون شلوغی."
        ),
        verbose_name="توضیحات معرفی",
    )
    hero_primary_cta_label = models.CharField(
        max_length=80,
        default="کشف محصولات",
        verbose_name="متن دکمه اصلی",
    )
    hero_primary_cta_url = models.CharField(
        max_length=300,
        default="#products",
        validators=[
            RegexValidator(
                regex=r"^(?:#|/(?!/)|https://)\\S*$",
                message="از نشانی داخلی، لنگر صفحه یا پیوند HTTPS استفاده کنید.",
            )
        ],
        verbose_name="پیوند دکمه اصلی",
    )
    body = RichTextField(
        blank=True,
        features=[
            "h2",
            "h3",
            "bold",
            "italic",
            "link",
            "ul",
            "ol",
            "blockquote",
            "hr",
            "image",
            "document-link",
        ],
        verbose_name="محتوای تکمیلی صفحه اصلی",
    )

    max_count = 1
    parent_page_types = ["wagtailcore.Page"]
    subpage_types = ["sitecms.ContentPage"]
    template = "sitecms/home_page.html"

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("hero_eyebrow"),
                FieldPanel("hero_title"),
                FieldPanel("hero_highlight"),
                FieldPanel("hero_description"),
                FieldPanel("hero_primary_cta_label"),
                FieldPanel("hero_primary_cta_url"),
            ],
            heading="بخش معرفی صفحه اصلی",
        ),
        FieldPanel("body"),
    ]

    search_fields = Page.search_fields + [
        index.SearchField("hero_title"),
        index.SearchField("hero_description"),
        index.SearchField("body"),
    ]

    class Meta:
        verbose_name = "صفحه اصلی"
        verbose_name_plural = "صفحه اصلی"


class ContentPage(Page):
    """Standard editorial page for about, help, policy and other site content."""

    intro = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="معرفی کوتاه",
    )
    body = RichTextField(
        blank=True,
        features=[
            "h2",
            "h3",
            "h4",
            "bold",
            "italic",
            "link",
            "ul",
            "ol",
            "blockquote",
            "hr",
            "image",
            "document-link",
            "embed",
        ],
        verbose_name="محتوای صفحه",
    )

    parent_page_types = ["sitecms.HomePage", "sitecms.ContentPage"]
    subpage_types = ["sitecms.ContentPage"]
    template = "sitecms/content_page.html"

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("body"),
    ]

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("body"),
    ]

    class Meta:
        verbose_name = "صفحه محتوایی"
        verbose_name_plural = "صفحات محتوایی"
