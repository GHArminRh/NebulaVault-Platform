from django.core.validators import URLValidator
from django.db import models
from cms.models.pluginmodel import CMSPlugin


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
