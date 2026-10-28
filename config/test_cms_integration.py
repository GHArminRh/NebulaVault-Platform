from django.conf import settings
from cms.plugin_pool import plugin_pool
from portal.models import CMSExternalImage, CMSUploadedImage
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
        self.assertIn(
            ("portal/cms_home_page.html", "صفحهٔ اصلی قابل ویرایش نبیولا والت"),
            settings.CMS_TEMPLATES,
        )

    def test_dynamic_content_plugins_are_registered(self):
        for plugin_name in (
            "LiveProductGridPlugin",
            "LivePricingGridPlugin",
            "LiveReleaseListPlugin",
            "LiveBlogListPlugin",
            "ExternalImagePlugin",
        ):
            self.assertIsNotNone(plugin_pool.get_plugin(plugin_name))

    def test_dynamic_plugin_templates_compile(self):
        for template_name in (
            "portal/plugins/live_products.html",
            "portal/plugins/live_pricing.html",
            "portal/plugins/live_releases.html",
            "portal/plugins/live_blog.html",
            "portal/plugins/external_image.html",
            "portal/plugins/uploaded_image.html",
        ):
            self.assertIsNotNone(get_template(template_name))

    def test_cms_image_models_belong_to_portal_migrations(self):
        self.assertEqual(CMSExternalImage._meta.app_label, "portal")
        self.assertEqual(CMSUploadedImage._meta.app_label, "portal")

    def test_uploads_are_disabled_without_durable_storage(self):
        self.assertFalse(settings.CMS_MEDIA_UPLOADS_ENABLED)
        self.assertNotIn("UploadedImagePlugin", plugin_pool.plugins)

    def test_existing_customer_and_api_routes_remain_resolvable(self):
        self.assertEqual(resolve("/accounts/login/").url_name, "login")
        self.assertIsNotNone(resolve("/api/v1/"))
        self.assertIsNotNone(resolve("/pages/example/"))
