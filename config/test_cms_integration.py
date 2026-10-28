from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase
from django.urls import resolve


class CmsIntegrationSmokeTests(SimpleTestCase):
    def test_cms_page_template_compiles(self):
        template = get_template("portal/cms_page.html")
        self.assertIsNotNone(template)

    def test_cms_apps_and_template_are_registered(self):
        self.assertIn("cms", settings.INSTALLED_APPS)
        self.assertIn("djangocms_text", settings.INSTALLED_APPS)
        self.assertIn("djangocms_frontend.contrib.grid", settings.INSTALLED_APPS)
        self.assertIn(
            ("portal/cms_page.html", "صفحهٔ عمومی نبیولا والت"),
            settings.CMS_TEMPLATES,
        )

    def test_existing_customer_and_api_routes_remain_resolvable(self):
        self.assertEqual(resolve("/accounts/login/").url_name, "login")
        self.assertIsNotNone(resolve("/api/v1/"))
        self.assertIsNotNone(resolve("/pages/example/"))
