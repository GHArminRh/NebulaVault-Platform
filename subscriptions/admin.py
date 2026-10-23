
from django.contrib import admin

from .models import Subscription, TrialRedemption


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
