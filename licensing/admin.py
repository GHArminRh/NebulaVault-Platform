from django.contrib import admin, messages

from .models import License, LicenseActivation
from .services import generate_license_key, _key_digest


class LicenseActivationInline(admin.TabularInline):
    model = LicenseActivation
    extra = 0
    can_delete = False
    fields = ("device_label", "app_version", "is_active", "first_activated_at", "last_seen_at", "deactivated_at")
    readonly_fields = ("device_label", "app_version", "first_activated_at", "last_seen_at", "deactivated_at", "is_active")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = (
        "key_prefix", "customer_email", "product_name", "status",
        "subscription_status", "expires_at", "activation_usage", "created_at",
    )
    list_filter = ("status", "subscription__kind", "subscription__status", "subscription__product")
    search_fields = (
        "key_prefix", "subscription__user__email", "subscription__user__username",
        "subscription__product__name", "subscription__plan__name",
    )
    autocomplete_fields = ("subscription",)
    readonly_fields = ("key_prefix", "key_digest", "created_at", "updated_at", "last_validated_at", "activation_usage")
    inlines = (LicenseActivationInline,)
    fieldsets = (
        ("License", {"fields": ("subscription", "status", "notes")}),
        ("Key security", {"fields": ("key_prefix", "key_digest"), "classes": ("collapse",)}),
        ("Activity", {"fields": ("created_at", "updated_at", "last_validated_at", "activation_usage")}),
    )
    list_select_related = ("subscription", "subscription__user", "subscription__product", "subscription__plan")

    @admin.display(description="Customer", ordering="subscription__user__email")
    def customer_email(self, obj):
        return obj.subscription.user.email

    @admin.display(description="Product", ordering="subscription__product__name")
    def product_name(self, obj):
        return obj.subscription.product.name

    @admin.display(description="Subscription", ordering="subscription__status")
    def subscription_status(self, obj):
        return obj.subscription.get_status_display()

    @admin.display(description="Expires", ordering="subscription__expires_at")
    def expires_at(self, obj):
        return obj.subscription.expires_at

    @admin.display(description="Devices")
    def activation_usage(self, obj):
        return f"{obj.activations.filter(is_active=True).count()} / {obj.activation_limit}"

    def save_model(self, request, obj, form, change):
        newly_issued_key = None
        if not change:
            newly_issued_key = generate_license_key()
            obj.key_prefix = newly_issued_key[:8]
            obj.key_digest = _key_digest(newly_issued_key)
        super().save_model(request, obj, form, change)
        if newly_issued_key:
            messages.success(
                request,
                "License created. Copy this key now; it is shown only once: " + newly_issued_key,
            )


@admin.register(LicenseActivation)
class LicenseActivationAdmin(admin.ModelAdmin):
    list_display = ("license", "device_label", "app_version", "is_active", "first_activated_at", "last_seen_at", "deactivated_at")
    list_filter = ("is_active", "first_activated_at", "license__status")
    search_fields = ("license__key_prefix", "license__subscription__user__email", "device_label", "app_version")
    list_select_related = ("license", "license__subscription", "license__subscription__user")
    readonly_fields = ("license", "fingerprint_digest", "device_label", "app_version", "first_activated_at", "last_seen_at", "deactivated_at", "is_active")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return super().has_view_permission(request, obj)
