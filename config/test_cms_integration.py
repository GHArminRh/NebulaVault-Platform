from django.conf import settings
from cms.plugin_pool import plugin_pool
from portal.models import CMSExternalImage, CMSUploadedImage
from django.template.loader import get_template
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import resolve

from cms.api import add_plugin
from cms.models import PageUrl
from cms.models.pluginmodel import CMSPlugin
from portal.cms_home import cms_home


class CmsIntegrationSmokeTests(SimpleTestCase):
    def test_cms_page_templates_compile(self):
        for template_name in (
            "portal/cms_page.html",
            "portal/cms_home_page.html",
        ):
            with self.subTest(template=template_name):
                self.assertIsNotNone(get_template(template_name))

    def test_public_root_is_routed_through_the_cms_home_view(self):
        self.assertIs(resolve("/").func, cms_home)

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
            "GridContainerPlugin",
            "GridRowPlugin",
            "GridColumnPlugin",
            "CardLayoutPlugin",
            "CardPlugin",
            "CardInnerPlugin",
            "AlertPlugin",
            "CodePlugin",
            "BlockquotePlugin",
            "FigurePlugin",
        ):
            self.assertIsNotNone(plugin_pool.get_plugin(plugin_name))

    def test_layout_plugins_are_allowed_in_general_editable_content(self):
        allowed = settings.CMS_PLACEHOLDER_CONF["content"]["plugins"]
        for plugin_name in settings.CMS_LAYOUT_PLUGINS:
            with self.subTest(plugin=plugin_name):
                self.assertIn(plugin_name, allowed)

    def test_homepage_has_a_dedicated_live_blog_placeholder(self):
        self.assertIn("blog", settings.CMS_PLACEHOLDER_CONF)
        self.assertIn("LiveBlogListPlugin", settings.CMS_PLACEHOLDER_CONF["blog"]["plugins"])

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


class CmsHomepageRoutingTests(TestCase):
    def setUp(self):
        self.site, _created = Site.objects.update_or_create(
            pk=settings.SITE_ID,
            defaults={"domain": "mydigigi.test", "name": "MyDigiGi CMS tests"},
        )

    def test_bootstrapped_cms_homepage_is_rendered_at_the_public_root(self):
        call_command("bootstrap_cms_homepage", verbosity=0)

        root_url = PageUrl.objects.filter(
            site=self.site,
            language="fa",
            path__in=("", "/"),
        ).select_related("page").first()
        self.assertIsNotNone(root_url)

        placeholders = {
            placeholder.slot: placeholder
            for placeholder in root_url.page.get_placeholders(language="fa")
        }
        self.assertIn("blog", placeholders)
        self.assertTrue(
            CMSPlugin.objects.filter(
                placeholder=placeholders["blog"],
                language="fa",
                plugin_type="LiveBlogListPlugin",
            ).exists()
        )

        marker = "CMS_ROOT_ROUTING_INTEGRATION_MARKER"
        add_plugin(
            placeholders["content"],
            "TextPlugin",
            "fa",
            body=f"<p>{marker}</p>",
        )

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, marker)
        self.assertTemplateUsed(response, "portal/cms_home_page.html")

    def test_storefront_fallback_is_preserved_without_a_cms_homepage(self):
        from cms.models import Page

        Page.objects.filter(site=self.site).delete()
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "کنترل در دست شما")
