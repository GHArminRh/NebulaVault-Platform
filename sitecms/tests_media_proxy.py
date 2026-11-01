from unittest.mock import patch

from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse

from .media_proxy import media_proxy_signature
from .storage import PrivateMediaS3Storage


class PrivateMediaProxyTests(TestCase):
    def test_invalid_signature_is_not_served(self):
        response = self.client.get(
            reverse("private-media-proxy", kwargs={"path": "images/example.png"}),
            {"signature": "invalid"},
        )
        self.assertEqual(response.status_code, 404)

    def test_signed_media_is_streamed_from_default_storage(self):
        path = "images/example.png"
        content = b"\x89PNG\r\n\x1a\nproxy-test"
        with patch(
            "sitecms.media_proxy.default_storage.open",
            return_value=ContentFile(content, name="example.png"),
        ) as open_file:
            response = self.client.get(
                reverse("private-media-proxy", kwargs={"path": path}),
                {"signature": media_proxy_signature(path)},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "image/png")
            self.assertEqual(response["X-Content-Type-Options"], "nosniff")
            self.assertEqual(b"".join(response.streaming_content), content)
            open_file.assert_called_once_with(path, "rb")

    def test_path_traversal_is_rejected_even_with_a_valid_signature(self):
        path = "images/../private/secret.png"
        response = self.client.get(
            reverse("private-media-proxy", kwargs={"path": path}),
            {"signature": media_proxy_signature(path)},
        )
        self.assertEqual(response.status_code, 404)

    def test_storage_returns_a_signed_same_origin_proxy_url(self):
        path = "images/example.png"
        url = PrivateMediaS3Storage().url(path)
        self.assertTrue(url.startswith("/media-proxy/images/example.png?"))
        self.assertIn(media_proxy_signature(path), url)
        self.assertNotIn("backblazeb2.com", url)
