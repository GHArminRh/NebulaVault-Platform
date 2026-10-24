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
    """Keep Django's full standard user administration experience."""
