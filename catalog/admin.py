from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .forms import ProductAdminForm, ReleaseAdminForm
from .models import Plan, Product, Release


class ReleaseInline(admin.TabularInline):
    model = Release
    extra = 0
    fields = ("version", "platform", "architecture", "installer_file", "sha256", "is_published")
    readonly_fields = ("sha256",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ("name", "slug_link", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ReleaseInline]

    @admin.display(description="Slug", ordering="slug")
    def slug_link(self, obj):
        """Open the public product page from the slug column."""
        url = reverse("portal:product_detail", kwargs={"slug": obj.slug})
        return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>', url, obj.slug)


@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
    form = ReleaseAdminForm
    list_display = (
        "product",
        "version",
        "platform",
        "architecture",
        "is_published",
        "published_at",
    )
    list_filter = ("platform", "architecture", "is_published")
    search_fields = ("product__name", "version")
    list_select_related = ("product",)
    readonly_fields = ("sha256", "created_at")
    fields = ("product", "version", "platform", "architecture", "installer_file", "download_url", "sha256", "release_notes", "is_published", "published_at", "created_at")


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "product",
        "duration_value",
        "duration_unit",
        "price_minor_units",
        "currency",
        "device_limit",
        "is_active",
    )
    list_filter = ("product", "duration_unit", "currency", "is_active")
    search_fields = ("name", "slug", "product__name")
    autocomplete_fields = ("product",)
    list_select_related = ("product",)
