from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group as DjangoAuthGroup

from .models import Group, StaffUser

# جایگزینی گروه پیش‌فرض جنگو با مدل اختصاصی برنامه.
admin.site.site_header = "Nebula Vault Administration"
admin.site.site_title = "Nebula Vault Admin"
admin.site.index_title = "Site administration"
admin.site.unregister(DjangoAuthGroup)


@admin.register(Group)
class StaffGroupAdmin(GroupAdmin):
    """Keep Django's full standard group-permissions admin experience."""


@admin.register(StaffUser)
class StaffUserAdmin(UserAdmin):
    """Keep Django's standard user admin while never displaying password hashes."""

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None:
            # Preserve Django's password entry fields when creating a staff user.
            return fieldsets
        return tuple(
            (title, {**options, "fields": tuple(name for name in options.get("fields", ()) if name != "password")})
            for title, options in fieldsets
            if any(name != "password" for name in options.get("fields", ()))
        )
