from types import SimpleNamespace

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from api.middleware import AdminOnlyV1ApiMiddleware


class AdminOnlyV1ApiMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = AdminOnlyV1ApiMiddleware(
            lambda request: HttpResponse("api response")
        )

    def test_anonymous_api_request_gets_branded_403_page(self):
        request = self.factory.get("/api/v1/products/")
        request.user = SimpleNamespace(
            is_authenticated=False,
            is_active=False,
            is_staff=False,
        )

        response = self.middleware(request)

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "دسترسی غیرمجاز", status_code=403)
        self.assertNotIn("Location", response.headers)
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_authenticated_non_staff_gets_403(self):
        request = self.factory.get("/api/v1/account/orders/")
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            is_staff=False,
        )

        response = self.middleware(request)

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "403", status_code=403)

    def test_active_staff_can_access_api(self):
        request = self.factory.get("/api/v1/products/")
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            is_staff=True,
        )

        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"api response")
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_desktop_licensing_api_is_not_blocked_by_this_middleware(self):
        request = self.factory.post("/api/licensing/validate/")
        request.user = SimpleNamespace(
            is_authenticated=False,
            is_active=False,
            is_staff=False,
        )

        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"api response")
