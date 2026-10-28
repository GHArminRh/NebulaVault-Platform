from types import SimpleNamespace

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from api.admin_pages import admin_page_required


class AdminPageRequiredTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_anonymous_user_gets_branded_403_without_redirect(self):
        request = self.factory.get("/api/v1/docs/")
        request.user = SimpleNamespace(
            is_authenticated=False, is_active=False, is_staff=False
        )
        response = admin_page_required(lambda request: HttpResponse("private"))(request)
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "دسترسی غیرمجاز", status_code=403)
        self.assertNotIn("Location", response.headers)
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")

    def test_non_staff_user_gets_branded_403(self):
        request = self.factory.get("/api/v1/schema/")
        request.user = SimpleNamespace(
            is_authenticated=True, is_active=True, is_staff=False
        )
        response = admin_page_required(lambda request: HttpResponse("private"))(request)
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "403", status_code=403)

    def test_active_staff_can_access_discovery_page(self):
        request = self.factory.get("/api/v1/docs/")
        request.user = SimpleNamespace(
            is_authenticated=True, is_active=True, is_staff=True
        )
        response = admin_page_required(lambda request: HttpResponse("docs"))(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"docs")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")
