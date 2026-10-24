"""Tests for the staff-only TinyMCE integration."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(TINYMCE_API_KEY="test-tinymce-key")
class StaffTinyMCEAdminTests(TestCase):
    def setUp(self):
        staff_user = get_user_model().objects.create_user(
            username="tinymce_staff",
            password="test-password-for-admin",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(
            staff_user, backend="django.contrib.auth.backends.ModelBackend"
        )

    def test_tinymce_loads_on_catalog_content_admin_form(self):
        response = self.client.get(reverse("admin:catalog_product_add"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "https://cdn.tiny.cloud/1/test-tinymce-key/tinymce/8/tinymce.min.js",
        )
        self.assertContains(response, "portal/js/tinymce_admin.js")

    def test_tinymce_does_not_load_on_unrelated_admin_form(self):
        response = self.client.get(reverse("admin:catalog_plan_add"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "tinymce.min.js")
