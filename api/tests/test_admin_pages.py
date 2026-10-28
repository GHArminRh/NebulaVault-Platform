from types import SimpleNamespace

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from api.admin_pages import admin_page_required


class AdminOnlyApiPageTests(SimpleTestCase):
    def setUp(self):
        self.request_factory = RequestFactory()
        self.view = admin_page_required(lambda request: HttpResponse("ok"))

    def test_anonymous_user_gets_forbidden_without_redirect(self):
        request = self.request_factory.get("/api/")
        request.user = SimpleNamespace(
            is_authenticated=False,
            is_active=False,
            is_staff=False,
        )

        response = self.view(request)

        self.assertEqual(response.status_code, 403)
        self.assertNotIn("Location", response.headers)

    def test_non_staff_user_gets_forbidden(self):
        request = self.request_factory.get("/api/")
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            is_staff=False,
        )

        response = self.view(request)

        self.assertEqual(response.status_code, 403)

    def test_active_staff_user_can_view_page(self):
        request = self.request_factory.get("/api/")
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            is_staff=True,
        )

        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")
        self.assertEqual(response["Cache-Control"], "private, no-store")
