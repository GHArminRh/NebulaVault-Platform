"""Tests for the staff-only django-tinymce integration."""

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image


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
        self.assertContains(response, 'data-upload-url="/admin/editor-upload/"')
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


    def test_image_upload_returns_a_stored_png(self):
        image_bytes = BytesIO()
        Image.new("RGB", (3, 2), color=(40, 120, 200)).save(image_bytes, format="JPEG")
        image_bytes.seek(0)

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    reverse("editor-image-upload"),
                    {"file": SimpleUploadedFile("source.jpg", image_bytes.read(), content_type="image/jpeg")},
                )

                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload["uploaded"], 1)
                self.assertTrue(payload["location"].endswith(".png"))
                saved_path = Path(media_root) / payload["location"].split("/media/", 1)[-1]
                self.assertTrue(saved_path.is_file())
                with Image.open(saved_path) as saved_image:
                    self.assertEqual(saved_image.format, "PNG")
                    self.assertEqual(saved_image.size, (3, 2))

    def test_image_upload_rejects_non_image_content(self):
        response = self.client.post(
            reverse("editor-image-upload"),
            {"file": SimpleUploadedFile("not-an-image.png", b"this is not an image", content_type="image/png")},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
