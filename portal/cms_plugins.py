"""Nebula Vault CMS plugins backed by structured and live domain data."""

from django.conf import settings
from django.db.models import Prefetch
from django.utils import timezone
from cms.models.pluginmodel import CMSPlugin
from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from blog.models import BlogPost
from catalog.models import Plan, Product, Release
from .models import (
    CMSExternalImage,
    CMSFAQList,
    CMSFeatureGrid,
    CMSHeroContent,
    CMSUploadedImage,
)


@plugin_pool.register_plugin
class HeroContentPlugin(CMSPluginBase):
    allowed_slots = ["hero"]
    model = CMSHeroContent
    name = "بنر اصلی (ساختاریافته)"
    module = "محتوای نبیولا والت"
    render_template = "portal/plugins/hero_content.html"
    cache = False
    fieldsets = (
        ("متن بنر", {"fields": ("eyebrow", "heading", "heading_accent", "description")}),
        ("دکمه‌ها", {"fields": (
            "primary_cta_label", "primary_cta_url",
            "secondary_cta_label", "secondary_cta_url",
        )}),
        ("نکته‌های اعتماد", {"fields": ("trust_item_1", "trust_item_2", "trust_item_3")}),
    )

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context["cms_hero"] = instance
        return context


@plugin_pool.register_plugin
class FeatureGridPlugin(CMSPluginBase):
    allowed_slots = ["features"]
    model = CMSFeatureGrid
    name = "کارت‌های امکانات (ساختاریافته)"
    module = "محتوای نبیولا والت"
    render_template = "portal/plugins/feature_grid.html"
    cache = False
    fieldsets = tuple(
        (f"ویژگی {index}", {"fields": tuple(
            f"feature_{index}_{field}"
            for field in ("icon", "number", "title", "description", "link_label", "link_url")
        )})
        for index in range(1, 4)
    )

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context["cms_features"] = instance
        return context


@plugin_pool.register_plugin
class FAQListPlugin(CMSPluginBase):
    allowed_slots = ["about"]
    model = CMSFAQList
    name = "پرسش‌های متداول (ساختاریافته)"
    module = "محتوای نبیولا والت"
    render_template = "portal/plugins/faq_list.html"
    cache = False
    fieldsets = tuple(
        (f"پرسش {index}", {"fields": (f"question_{index}", f"answer_{index}")})
        for index in range(1, 4)
    )

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context["cms_faq"] = instance
        return context


@plugin_pool.register_plugin
class LiveProductGridPlugin(CMSPluginBase):
    allowed_slots = ["products"]
    model = CMSPlugin
    name = "محصولات زنده"
    module = "محتوای پویای نبیولا"
    render_template = "portal/plugins/live_products.html"
    cache = False

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context["cms_products"] = (
            Product.objects.filter(is_active=True)
            .prefetch_related(Prefetch("plans", queryset=Plan.objects.filter(is_active=True)))
            .order_by("name")[:6]
        )
        return context


@plugin_pool.register_plugin
class LivePricingGridPlugin(CMSPluginBase):
    # Kept for compatibility with the legacy pricing placeholder. The current
    # homepage intentionally has no pricing section; /pricing/ remains canonical.
    allowed_slots = ["pricing"]
    model = CMSPlugin
    name = "تعرفه‌های زنده"
    module = "محتوای پویای نبیولا"
    render_template = "portal/plugins/live_pricing.html"
    cache = False

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context["cms_plans"] = (
            Plan.objects.filter(is_active=True, product__is_active=True)
            .select_related("product")
            .order_by("sort_order", "price_minor_units")[:12]
        )
        return context


@plugin_pool.register_plugin
class LiveReleaseListPlugin(CMSPluginBase):
    allowed_slots = ["releases"]
    model = CMSPlugin
    name = "نسخه‌های منتشرشده"
    module = "محتوای پویای نبیولا"
    render_template = "portal/plugins/live_releases.html"
    cache = False

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context["cms_releases"] = (
            Release.objects.filter(
                is_published=True,
                product__is_active=True,
            )
            .select_related("product")
            .order_by("-published_at", "-created_at")[:8]
        )
        return context


@plugin_pool.register_plugin
class LiveBlogListPlugin(CMSPluginBase):
    allowed_slots = ["blog"]
    model = CMSPlugin
    name = "مقالات تازه"
    module = "محتوای پویای نبیولا"
    render_template = "portal/plugins/live_blog.html"
    cache = False

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context["cms_blog_posts"] = (
            BlogPost.objects.filter(
                status=BlogPost.Status.PUBLISHED,
                published_at__lte=timezone.now(),
            )
            .order_by("-is_featured", "-published_at")[:6]
        )
        return context


@plugin_pool.register_plugin
class ExternalImagePlugin(CMSPluginBase):
    allowed_slots = ["hero", "content", "features", "about"]
    model = CMSExternalImage
    name = "تصویر با آدرس اینترنتی"
    module = "محتوای پویای نبیولا"
    render_template = "portal/plugins/external_image.html"
    cache = True

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context["cms_image"] = instance
        return context


# Do not expose an upload control while the deployment has no durable storage.
if settings.CMS_MEDIA_UPLOADS_ENABLED:
    @plugin_pool.register_plugin
    class UploadedImagePlugin(CMSPluginBase):
        allowed_slots = ["hero", "content", "features", "about"]
        model = CMSUploadedImage
        name = "تصویر بارگذاری‌شده"
        module = "محتوای پویای نبیولا"
        render_template = "portal/plugins/uploaded_image.html"
        cache = True

        def render(self, context, instance, placeholder):
            context = super().render(context, instance, placeholder)
            context["cms_image"] = instance
            return context
