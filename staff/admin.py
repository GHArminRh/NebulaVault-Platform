from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group as DjangoAuthGroup
from filer.admin.permissionadmin import PermissionAdmin
from filer.models import FolderPermission

from .models import Group, StaffUser

# جایگزینی گروه پیش‌فرض جنگو با مدل اختصاصی برنامه.
admin.site.site_header = "Nebula Vault Administration"
admin.site.site_title = "Nebula Vault Admin"
admin.site.index_title = "Site administration"
admin.site.unregister(DjangoAuthGroup)


class StaffFilerPermissionAdmin(PermissionAdmin):
    """Avoid requiring an admin registration for Django auth.Group autocomplete.

    Staff permissions use the UUID-backed staff.Group model. django-filer
    retains its legacy auth.Group relation for folder permissions, but that
    legacy model must not appear as a second Groups section in the admin.
    """

    autocomplete_fields = ("user", "folder")


admin.site.unregister(FolderPermission)
admin.site.register(FolderPermission, StaffFilerPermissionAdmin)


@admin.register(Group)
class StaffGroupAdmin(GroupAdmin):
    """Keep Django standard group-permissions admin experience."""


@admin.register(StaffUser)
class StaffUserAdmin(UserAdmin):
    """Keep Django standard user admin while never displaying password hashes."""

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None:
            return fieldsets
        return tuple(
            (title, {**options, "fields": tuple(name for name in options.get("fields", ()) if name != "password")})
            for title, options in fieldsets
            if any(name != "password" for name in options.get("fields", ()))
        )
