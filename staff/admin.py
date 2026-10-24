from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group as DjangoAuthGroup

from .models import Group, StaffUser

# Replace Django's built-in Group registration with the app-owned model.
admin.site.unregister(DjangoAuthGroup)


@admin.register(Group)
class StaffGroupAdmin(GroupAdmin):
    """Keep Django's full standard group-permissions admin experience."""


@admin.register(StaffUser)
class StaffUserAdmin(UserAdmin):
    """Keep Django's full standard user administration experience."""
