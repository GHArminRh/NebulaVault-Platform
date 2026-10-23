from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group as DjangoAuthGroup

from .models import Customer, Group, StaffUser

# Replace Django's integer-PK group model in the admin with the UUID-backed
# equivalent from accounts, while retaining Django's standard group UI.
admin.site.unregister(DjangoAuthGroup)


@admin.register(Group)
class AccountsGroupAdmin(DjangoGroupAdmin):
    """Manage UUID4 permission groups under the Accounts app."""


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
