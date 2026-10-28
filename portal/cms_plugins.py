"""Nebula Vault CMS plugins backed by live product, pricing, release and blog data."""
from django.conf import settings
from django.utils import timezone
from cms.models.pluginmodel import CMSPlugin
from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from blog.models import BlogPost
from catalog.models import Plan, Product, Release
from .models import CMSExternalImage, CMSUploadedImage


@plugin_pool.register_plugin
class LiveProductGridPlugin(CMSPluginBase):
    model = CMSPlugin
    name = "محصولات زنده"
    module = "محتوای پویای نبیولا"
    render_template = "portal/plugins/live_products.html"
    cache = False

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context["cms_products"] = (
            Product.objects.filter(is_active=True)
            .prefetch_related("plans")
            .order_by("name")[:6]
        )
        return context


@plugin_pool.register_plugin
class LivePricingGridPlugin(CMSPluginBase):
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
        model = CMSUploadedImage
        name = "تصویر بارگذاری‌شده"
        module = "محتوای پویای نبیولا"
        render_template = "portal/plugins/uploaded_image.html"
        cache = True

        def render(self, context, instance, placeholder):
            context = super().render(context, instance, placeholder)
            context["cms_image"] = instance
            return context
