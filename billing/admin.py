from django.contrib import admin
from import_export import resources
from import_export.admin import ExportMixin

from .models import PaymentAttempt, PaymentOrder


class PaymentOrderResource(resources.ModelResource):
    class Meta:
        model = PaymentOrder
        fields = ("order_number", "user", "plan", "amount_minor_units", "currency", "status", "created_at", "paid_at", "updated_at")
        export_order = fields


class PaymentAttemptResource(resources.ModelResource):
    class Meta:
        model = PaymentAttempt
        fields = ("id", "order", "provider", "amount_minor_units", "currency", "status", "confirmed_at", "created_at", "updated_at")
        export_order = fields


class PaymentAttemptInline(admin.TabularInline):
    model = PaymentAttempt
    extra = 0
    can_delete = False
    show_change_link = True
    fields = ("provider", "provider_reference", "amount_minor_units", "currency", "status", "confirmed_at", "created_at")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PaymentOrder)
class PaymentOrderAdmin(ExportMixin, admin.ModelAdmin):
    resource_classes = (PaymentOrderResource,)
    list_display = ("order_number", "user", "plan", "amount_minor_units", "currency", "status", "created_at", "paid_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("order_number", "user__email", "user__username", "plan__name")
    readonly_fields = ("order_number", "user", "plan", "amount_minor_units", "currency", "status", "paid_at", "created_at", "updated_at")
    inlines = (PaymentAttemptInline,)
    date_hierarchy = "created_at"
    list_select_related = ("user", "plan")

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(ExportMixin, admin.ModelAdmin):
    resource_classes = (PaymentAttemptResource,)
    list_display = ("id", "order", "provider", "provider_reference", "amount_minor_units", "currency", "status", "created_at", "confirmed_at")
    list_filter = ("status", "provider", "currency", "created_at")
    search_fields = ("provider_reference", "order__order_number", "order__user__email")
    readonly_fields = ("order", "provider", "provider_reference", "idempotency_key", "amount_minor_units", "currency", "status", "confirmed_at", "created_at", "updated_at")
    date_hierarchy = "created_at"
    list_select_related = ("order", "order__user")

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
