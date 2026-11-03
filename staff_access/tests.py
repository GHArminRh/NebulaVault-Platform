import uuid
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as DjangoAuthGroup
from django.test import TestCase

from .models import Group


class StaffAccessTests(TestCase):
    def test_staff_user_uses_uuid4_primary_key(self):
        staff = get_user_model().objects.create_user(username="uuid_staff", email="uuid_staff@example.com", password="Secure-staff-password-2026!")
        self.assertIsInstance(staff.pk, uuid.UUID)
        self.assertEqual(staff.pk.version, 4)

    def test_staff_uuid_session_survives_following_request(self):
        staff = get_user_model().objects.create_superuser(username="uuid_admin", email="uuid_admin@example.com", password="Secure-admin-password-2026!")
        self.client.force_login(staff, backend="django.contrib.auth.backends.ModelBackend")
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(self.client.session["_auth_user_id"]), str(staff.pk))

    def test_permission_group_uses_uuid4_primary_key(self):
        group = Group.objects.create(name="UUID test group")
        self.assertIsInstance(group.pk, uuid.UUID)
        self.assertEqual(group.pk.version, 4)

    def test_staff_user_can_use_custom_uuid_permission_group(self):
        staff = get_user_model().objects.create_user(username="group_member", email="group_member@example.com", password="Secure-staff-password-2026!")
        group = Group.objects.create(name="staff-test-group")
        staff.groups.add(group)
        self.assertIn(group, staff.groups.all())
        self.assertIn(staff, group.user_set.all())

    def test_builtin_integer_group_is_not_registered_in_admin(self):
        self.assertNotIn(DjangoAuthGroup, admin.site._registry)
        self.assertIn(Group, admin.site._registry)
