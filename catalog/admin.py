
from django.contrib import admin

from .models import Plan, Product, Release


class ReleaseInline(admin.TabularInline):
    model = Release
    extra = 0
    fields = ("version", "platform", "architecture", "installer_file", "sha256", "is_published")
    readonly_fields = ("sha256",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ReleaseInline]


@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
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
