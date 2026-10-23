
from django.contrib import admin

from .models import (
    Subscription,
    SubscriptionRenewal,
    TrialRedemption,
)


@admin.register(TrialRedemption)
class TrialRedemptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "product",
        "started_at",
        "ends_at",
        "created_at",
    )
    list_filter = ("product", "started_at")
    search_fields = (
        "user__username",
        "user__email",
        "product__name",
    )
    autocomplete_fields = ("user", "product")
    list_select_related = ("user", "product")
    readonly_fields = ("created_at",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "product",
        "kind",
        "status",
        "plan",
        "starts_at",
        "expires_at",
    )
    list_filter = ("kind", "status", "product")
    search_fields = (
        "user__username",
        "user__email",
        "product__name",
        "plan__name",
    )
    autocomplete_fields = (
        "user",
        "product",
        "plan",
        "trial_redemption",
    )
    list_select_related = (
        "user",
        "product",
        "plan",
        "trial_redemption",
    )
    readonly_fields = ("created_at", "updated_at")



@admin.register(SubscriptionRenewal)
class SubscriptionRenewalAdmin(admin.ModelAdmin):
    list_display = (
        "subscription",
        "payment_reference",
        "amount_minor_units",
        "currency",
        "previous_expires_at",
        "new_expires_at",
        "created_at",
    )
    list_filter = ("currency", "created_at")
    search_fields = (
        "payment_reference",
        "subscription__user__email",
        "subscription__user__username",
    )
    list_select_related = (
        "subscription",
        "subscription__user",
        "subscription__product",
    )
    readonly_fields = (
        "subscription",
        "payment_reference",
        "previous_expires_at",
        "new_expires_at",
        "amount_minor_units",
        "currency",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
