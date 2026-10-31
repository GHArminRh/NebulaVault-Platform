from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import models
from cms.models.pluginmodel import CMSPlugin


def validate_cms_link(value):
    """Allow safe site-relative or explicitly supported external CTA links."""
    if not value:
        return
    value = value.strip()
    if not value or any(character.isspace() for character in value):
        raise ValidationError("نشانی پیوند معتبر نیست.")
    if value.startswith("/") and not value.startswith("//"):
        return
    if value.startswith("#"):
        return

    parsed = urlsplit(value)
    if parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username and not parsed.password:
        return
    if parsed.scheme in {"mailto", "tel"} and parsed.path:
        return
    raise ValidationError(
        "فقط نشانی داخلی، پیوند امن HTTP(S)، ایمیل یا شماره تلفن مجاز است."
    )


class CMSHeroContent(CMSPlugin):
    """Structured hero copy; presentation markup stays in the plugin template."""

    cmsplugin_ptr = models.OneToOneField(
        CMSPlugin, on_delete=models.CASCADE, related_name="portal_hero_content",
        parent_link=True, primary_key=True,
    )
    eyebrow = models.CharField(max_length=180, blank=True, default="", verbose_name="متن بالای عنوان")
    heading = models.CharField(max_length=200, blank=True, default="", verbose_name="عنوان اصلی")
    heading_accent = models.CharField(max_length=200, blank=True, default="", verbose_name="عبارت رنگی عنوان")
    description = models.TextField(blank=True, default="", verbose_name="توضیح کوتاه")
    primary_cta_label = models.CharField(max_length=80, blank=True, default="", verbose_name="متن دکمهٔ اصلی")
    primary_cta_url = models.CharField(
        max_length=500, blank=True, default="", validators=[validate_cms_link],
        verbose_name="پیوند دکمهٔ اصلی",
    )
    secondary_cta_label = models.CharField(max_length=80, blank=True, default="", verbose_name="متن دکمهٔ دوم")
    secondary_cta_url = models.CharField(
        max_length=500, blank=True, default="", validators=[validate_cms_link],
        verbose_name="پیوند دکمهٔ دوم",
    )
    trust_item_1 = models.CharField(max_length=120, blank=True, default="", verbose_name="نکتهٔ اعتماد ۱")
    trust_item_2 = models.CharField(max_length=120, blank=True, default="", verbose_name="نکتهٔ اعتماد ۲")
    trust_item_3 = models.CharField(max_length=120, blank=True, default="", verbose_name="نکتهٔ اعتماد ۳")
    legacy_source = models.TextField(blank=True, default="", editable=False, verbose_name="نسخهٔ پشتیبان محتوای قبلی")

    class Meta:
        verbose_name = "محتوای ساختاریافتهٔ بنر اصلی"
        verbose_name_plural = "محتوای ساختاریافتهٔ بنر اصلی"

    def __str__(self):
        return self.heading or self.eyebrow or "بنر اصلی"


class CMSFeatureGrid(CMSPlugin):
    """Three editable feature cards with fixed, template-owned markup."""

    cmsplugin_ptr = models.OneToOneField(
        CMSPlugin, on_delete=models.CASCADE, related_name="portal_feature_grid",
        parent_link=True, primary_key=True,
    )
    feature_1_icon = models.CharField(max_length=24, blank=True, default="", verbose_name="نماد ویژگی ۱")
    feature_1_number = models.CharField(max_length=8, blank=True, default="", verbose_name="شمارهٔ ویژگی ۱")
    feature_1_title = models.CharField(max_length=140, blank=True, default="", verbose_name="عنوان ویژگی ۱")
    feature_1_description = models.TextField(blank=True, default="", verbose_name="توضیح ویژگی ۱")
    feature_1_link_label = models.CharField(max_length=100, blank=True, default="", verbose_name="متن پیوند ویژگی ۱")
    feature_1_link_url = models.CharField(max_length=500, blank=True, default="", validators=[validate_cms_link], verbose_name="پیوند ویژگی ۱")
    feature_2_icon = models.CharField(max_length=24, blank=True, default="", verbose_name="نماد ویژگی ۲")
    feature_2_number = models.CharField(max_length=8, blank=True, default="", verbose_name="شمارهٔ ویژگی ۲")
    feature_2_title = models.CharField(max_length=140, blank=True, default="", verbose_name="عنوان ویژگی ۲")
    feature_2_description = models.TextField(blank=True, default="", verbose_name="توضیح ویژگی ۲")
    feature_2_link_label = models.CharField(max_length=100, blank=True, default="", verbose_name="متن پیوند ویژگی ۲")
    feature_2_link_url = models.CharField(max_length=500, blank=True, default="", validators=[validate_cms_link], verbose_name="پیوند ویژگی ۲")
    feature_3_icon = models.CharField(max_length=24, blank=True, default="", verbose_name="نماد ویژگی ۳")
    feature_3_number = models.CharField(max_length=8, blank=True, default="", verbose_name="شمارهٔ ویژگی ۳")
    feature_3_title = models.CharField(max_length=140, blank=True, default="", verbose_name="عنوان ویژگی ۳")
    feature_3_description = models.TextField(blank=True, default="", verbose_name="توضیح ویژگی ۳")
    feature_3_link_label = models.CharField(max_length=100, blank=True, default="", verbose_name="متن پیوند ویژگی ۳")
    feature_3_link_url = models.CharField(max_length=500, blank=True, default="", validators=[validate_cms_link], verbose_name="پیوند ویژگی ۳")
    legacy_source = models.TextField(blank=True, default="", editable=False, verbose_name="نسخهٔ پشتیبان محتوای قبلی")

    class Meta:
        verbose_name = "کارت‌های امکانات"
        verbose_name_plural = "کارت‌های امکانات"

    def __str__(self):
        return "بخش امکانات صفحهٔ اصلی"


class CMSFAQList(CMSPlugin):
    """Three editable FAQ entries with semantic details/summary output."""

    cmsplugin_ptr = models.OneToOneField(
        CMSPlugin, on_delete=models.CASCADE, related_name="portal_faq_list",
        parent_link=True, primary_key=True,
    )
    question_1 = models.CharField(max_length=240, blank=True, default="", verbose_name="پرسش ۱")
    answer_1 = models.TextField(blank=True, default="", verbose_name="پاسخ ۱")
    question_2 = models.CharField(max_length=240, blank=True, default="", verbose_name="پرسش ۲")
    answer_2 = models.TextField(blank=True, default="", verbose_name="پاسخ ۲")
    question_3 = models.CharField(max_length=240, blank=True, default="", verbose_name="پرسش ۳")
    answer_3 = models.TextField(blank=True, default="", verbose_name="پاسخ ۳")
    legacy_source = models.TextField(blank=True, default="", editable=False, verbose_name="نسخهٔ پشتیبان محتوای قبلی")

    class Meta:
        verbose_name = "پرسش‌های متداول"
        verbose_name_plural = "پرسش‌های متداول"

    def __str__(self):
        return self.question_1 or "پرسش‌های متداول"


class CMSExternalImage(CMSPlugin):
    """An image block referencing a durable, externally hosted HTTP(S) image."""

    image_url = models.URLField(
        max_length=1000,
        validators=[URLValidator(schemes=["https", "http"])],
        verbose_name="آدرس تصویر",
        help_text="برای ماندگاری تصویر، از میزبان رسانه‌ای پایدار استفاده کنید.",
    )
    alt_text = models.CharField(max_length=240, verbose_name="متن جایگزین")
    caption = models.CharField(max_length=320, blank=True, verbose_name="زیرنویس")

    class Meta:
        app_label = "portal"
        verbose_name = "بلوک تصویر خارجی"
        verbose_name_plural = "بلوک‌های تصویر خارجی"

    def __str__(self):
        return self.alt_text or self.image_url


class CMSUploadedImage(CMSPlugin):
    """An uploaded CMS image stored only when durable media storage is configured."""

    image = models.ImageField(
        upload_to="cms/images/%Y/%m/",
        verbose_name="فایل تصویر",
    )
    alt_text = models.CharField(max_length=240, verbose_name="متن جایگزین")
    caption = models.CharField(max_length=320, blank=True, verbose_name="زیرنویس")

    class Meta:
        app_label = "portal"
        verbose_name = "تصویر بارگذاری‌شدهٔ CMS"
        verbose_name_plural = "تصاویر بارگذاری‌شدهٔ CMS"

    def __str__(self):
        return self.alt_text or str(self.image)
