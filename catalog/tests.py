"""Tests for the staff-only django-tinymce integration."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


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

    def test_tinymce_widget_loads_on_catalog_content_admin_form(self):
        response = self.client.get(reverse("admin:catalog_product_add"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "tinymce/tinymce.min.js")
        self.assertContains(response, "tinymce/init_tinymce.js")
        self.assertContains(response, "portal/js/tinymce_upload.js")
        self.assertContains(response, "id_description")
        self.assertNotContains(response, "cdn.tiny.cloud")

    def test_tinymce_widget_loads_on_release_notes_admin_form(self):
        response = self.client.get(reverse("admin:catalog_release_add"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "tinymce/tinymce.min.js")
        self.assertContains(response, "id_release_notes")

    def test_tinymce_does_not_load_on_unrelated_admin_form(self):
        response = self.client.get(reverse("admin:catalog_plan_add"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "tinymce/tinymce.min.js")
        self.assertNotContains(response, "cdn.tiny.cloud")
