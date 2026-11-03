from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group as DjangoAuthGroup

from .models import Group, StaffUser

admin.site.unregister(DjangoAuthGroup)


@admin.register(Group)
class StaffGroupAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)
    filter_horizontal = ("permissions",)


@admin.register(StaffUser)
class StaffUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_active")
    ordering = ("username",)
    readonly_fields = ("last_login", "date_joined")
