"""Seed only the two homepage regions that were empty in the live CMS database.

This is deliberately a one-time data migration. It never overwrites existing
editor content, and future intentional deletions are not automatically undone.
"""

from django.conf import settings
from django.db import migrations


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


def seed_empty_homepage_regions(apps, schema_editor):
    # Use runtime CMS APIs here because plugin creation must go through the
    # registered plugin pool (TextPlugin and the site's live product plugin).
    from django.contrib.sites.models import Site

    from cms.api import add_plugin
    from cms.models import PageContent, PageUrl, Placeholder
    from cms.models.pluginmodel import CMSPlugin
    from cms.utils.placeholder import rescan_placeholders_for_obj

    site = Site.objects.filter(pk=settings.SITE_ID).first()
    if site is None:
        return

    root_url = (
        PageUrl.objects.filter(site=site, language="fa", path__in=("", "/"))
        .select_related("page")
        .first()
    )
    if root_url is None:
        return

    page_content = PageContent.objects.filter(
        page_id=root_url.page_id,
        language="fa",
    ).first()
    if page_content is None:
        return

    placeholders = {
        placeholder.slot: placeholder
        for placeholder in Placeholder.objects.get_for_obj(page_content)
    }
    if not {"hero", "products"}.issubset(placeholders):
        placeholders.update(rescan_placeholders_for_obj(page_content))

    defaults = (
        ("hero", "TextPlugin", {"body": HERO_COPY}),
        ("products", "LiveProductGridPlugin", {}),
    )
    for slot, plugin_type, plugin_data in defaults:
        placeholder = placeholders.get(slot)
        if placeholder is None:
            continue
        # Any existing plugin means this region is editor-owned. Do not replace
        # it, even if its plugin type differs from the original seed.
        if CMSPlugin.objects.filter(
            placeholder_id=placeholder.pk,
            language="fa",
        ).exists():
            continue
        add_plugin(placeholder, plugin_type, "fa", **plugin_data)


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0045_pageurl_site_unique_path"),
        ("djangocms_text", "0004_remove_old_ckeditor_table"),
        ("portal", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            seed_empty_homepage_regions,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
