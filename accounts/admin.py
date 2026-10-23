from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Customer, StaffUser


@admin.register(StaffUser)
class StaffUserAdmin(UserAdmin):
    """Keep Django's familiar staff administration with UUID-backed users."""

    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_active")
    ordering = ("username",)
    readonly_fields = ("last_login", "date_joined")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("email", "username", "first_name", "last_name", "is_active", "date_joined")
    list_filter = ("is_active", "date_joined")
    search_fields = ("email", "username", "first_name", "last_name")
    readonly_fields = ("last_login", "date_joined")
    ordering = ("-date_joined",)
