from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from .forms import ProductAdminForm, ReleaseAdminForm
from .models import Plan, Product, Release


class ProductResource(resources.ModelResource):
    class Meta:
        model = Product
        fields = ("id", "name", "slug", "description", "website_url", "is_active")
        export_order = fields
        import_id_fields = ("slug",)


class ReleaseResource(resources.ModelResource):
    product = fields.Field(attribute="product", column_name="product_id", widget=ForeignKeyWidget(Product, field="id"))

    class Meta:
        model = Release
        fields = ("id", "product", "version", "platform", "architecture", "download_url", "release_notes", "is_published", "published_at")
        export_order = fields
        import_id_fields = ("product", "version", "platform", "architecture")
        skip_unchanged = True
        report_skipped = True


class PlanResource(resources.ModelResource):
    product = fields.Field(attribute="product", column_name="product_id")

    class Meta:
        model = Plan
        fields = ("id", "product", "name", "duration_unit", "duration_value", "price_minor_units", "currency", "device_limit", "is_active", "sort_order")
        export_order = fields
        import_id_fields = ("product", "name")
        skip_unchanged = True
        report_skipped = True


class ReleaseInline(admin.TabularInline):
    model = Release
    extra = 0
    fields = ("version", "platform", "architecture", "installer_file", "sha256", "is_published")
    readonly_fields = ("sha256",)


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_classes = (ProductResource,)
    form = ProductAdminForm
    list_display = ("name", "slug_link", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ReleaseInline]

    @admin.display(description="Slug", ordering="slug")
    def slug_link(self, obj):
        url = reverse("portal:product_detail", kwargs={"slug": obj.slug})
        return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>', url, obj.slug)


@admin.register(Release)
class ReleaseAdmin(ImportExportModelAdmin):
    resource_classes = (ReleaseResource,)
    form = ReleaseAdminForm
    list_display = ("product", "version", "platform", "architecture", "is_published", "published_at")
    list_filter = ("platform", "architecture", "is_published")
    search_fields = ("product__name", "version")
    list_select_related = ("product",)
    readonly_fields = ("sha256", "created_at")
    fields = ("product", "version", "platform", "architecture", "installer_file", "download_url", "sha256", "release_notes", "is_published", "published_at", "created_at")


@admin.register(Plan)
class PlanAdmin(ImportExportModelAdmin):
    resource_classes = (PlanResource,)
    list_display = ("name", "product", "duration_value", "duration_unit", "price_minor_units", "currency", "device_limit", "is_active")
    list_filter = ("product", "duration_unit", "currency", "is_active")
    search_fields = ("name", "slug", "product__name")
    autocomplete_fields = ("product",)
    list_select_related = ("product",)
