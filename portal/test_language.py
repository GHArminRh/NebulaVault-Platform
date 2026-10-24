from django.test import RequestFactory, SimpleTestCase
from django.utils import translation

from portal.middleware import InterfaceLanguageMiddleware


class InterfaceLanguageMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.middleware = InterfaceLanguageMiddleware(lambda request: None)
        self.factory = RequestFactory()

    def tearDown(self):
        translation.deactivate_all()

    def test_public_site_uses_persian(self):
        request = self.factory.get("/accounts/login/")
        self.middleware.process_request(request)
        self.assertEqual(translation.get_language(), "fa")
        self.assertEqual(request.LANGUAGE_CODE, "fa")
        self.assertEqual(request.site_language, "fa")

    def test_admin_login_keeps_english(self):
        request = self.factory.get("/admin/login/")
        self.middleware.process_request(request)
        self.assertEqual(translation.get_language(), "en-us")
        self.assertEqual(request.LANGUAGE_CODE, "en-us")
        self.assertEqual(request.site_language, "en")
