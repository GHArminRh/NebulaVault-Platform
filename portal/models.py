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
        verbose_name = "بلوک تصویر خارجی"
        verbose_name_plural = "بلوک‌های تصویر خارجی"

    def __str__(self):
        return self.alt_text or self.image_url
