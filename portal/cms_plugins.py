"""Nebula Vault CMS plugins backed by live product, pricing, release and blog data."""
from django.conf import settings
from django.db.models import Prefetch
from django.utils import timezone
from cms.models.pluginmodel import CMSPlugin
from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from djangocms_text.cms_plugins import TextPlugin

from blog.models import BlogPost
from catalog.models import Plan, Product, Release
from .models import CMSExternalImage, CMSUploadedImage


@plugin_pool.register_plugin
class HeroTextPlugin(TextPlugin):
    """Text editor dedicated to the homepage hero's stable presentation wrapper."""

    allowed_slots = ["hero"]
    name = "متن بنر اصلی"
    module = "محتوای نبیولا"
    render_template = "portal/plugins/hero_text.html"
    cache = False


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
