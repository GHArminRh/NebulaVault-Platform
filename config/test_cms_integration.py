from importlib import import_module

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.migrations.loader import MigrationLoader
from django.template.loader import get_template
from django.test import SimpleTestCase, TestCase
from django.urls import resolve
from unittest.mock import patch

from cms.api import add_plugin, create_page
from cms.models import PageUrl, Placeholder
from cms.models.pluginmodel import CMSPlugin
from cms.plugin_pool import plugin_pool
from catalog.models import Plan, Product
from portal.cms_home import cms_home
from portal.models import (
    CMSExternalImage,
    CMSFAQList,
    CMSFeatureGrid,
    CMSHeroContent,
    CMSUploadedImage,
)


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

    def test_authentication_middleware_satisfies_cms_and_uuid_user_resolution(self):
        middleware = settings.MIDDLEWARE
        self.assertIn(
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            middleware,
        )
        self.assertIn(
            "accounts.middleware.UUIDCompatibleAuthenticationMiddleware",
            middleware,
        )
        self.assertLess(
            middleware.index("django.contrib.auth.middleware.AuthenticationMiddleware"),
            middleware.index("accounts.middleware.UUIDCompatibleAuthenticationMiddleware"),
        )
        self.assertLess(
            middleware.index("accounts.middleware.UUIDCompatibleAuthenticationMiddleware"),
            middleware.index("cms.middleware.user.CurrentUserMiddleware"),
        )

    def test_cms_apps_and_template_are_registered(self):
        self.assertIn("cms", settings.INSTALLED_APPS)
        self.assertIn("djangocms_text", settings.INSTALLED_APPS)
        self.assertIn("djangocms_link", settings.INSTALLED_APPS)
        self.assertIn("djangocms_frontend.contrib.link", settings.INSTALLED_APPS)
        self.assertIn("djangocms_frontend.contrib.grid", settings.INSTALLED_APPS)
        self.assertIn("cms_site_seed", settings.INSTALLED_APPS)
        self.assertEqual(settings.CMS_TREE_BACKEND, "mptree")
        self.assertFalse(settings.CMS_PERMISSION)
        self.assertNotIn("treebeard", settings.INSTALLED_APPS)
        self.assertIn(
            ("portal/cms_page.html", "صفحهٔ عمومی نبیولا والت"),
            settings.CMS_TEMPLATES,
        )
        self.assertIn(
            ("portal/cms_home_page.html", "صفحهٔ اصلی قابل ویرایش نبیولا والت"),
            settings.CMS_TEMPLATES,
        )

    def test_page_templates_declare_only_their_supported_placeholders(self):
        home_source = get_template("portal/cms_home_page.html").template.source
        generic_source = get_template("portal/cms_page.html").template.source
        home_slots = ("hero", "content", "products", "features", "releases", "blog", "about")
        for slot in home_slots:
            with self.subTest(template="home", slot=slot):
                self.assertIn('{% placeholder "' + slot + '"', home_source)
                self.assertIn(slot, settings.CMS_PLACEHOLDER_CONF)
        self.assertNotIn('{% placeholder "pricing"', home_source)
        self.assertIn('{% placeholder "content"', generic_source)
        for slot in ("hero", "products", "features", "releases", "blog", "about"):
            self.assertNotIn('{% placeholder "' + slot + '"', generic_source)

    def test_structured_cta_links_reject_unsafe_schemes(self):
        from django.core.exceptions import ValidationError
        from portal.models import validate_cms_link

        validate_cms_link("/products/")
        validate_cms_link("https://example.com/page")
        with self.assertRaises(ValidationError):
            validate_cms_link("javascript:alert(1)")
        with self.assertRaises(ValidationError):
            validate_cms_link("//example.com/path")

    def test_dynamic_content_plugins_are_registered(self):
        for plugin_name in (
            "HeroContentPlugin",
            "FeatureGridPlugin",
            "FAQListPlugin",
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
            "TextLinkPlugin",
        ):
            self.assertIsNotNone(plugin_pool.get_plugin(plugin_name))

    def test_link_button_plugin_is_available_in_editor_placeholders(self):
        self.assertIn(
            "TextLinkPlugin",
            settings.CMS_PLACEHOLDER_CONF["content"]["plugins"],
        )
        self.assertIn(
            "HeroContentPlugin",
            settings.CMS_PLACEHOLDER_CONF["hero"]["plugins"],
        )
        self.assertNotIn("TextPlugin", settings.CMS_PLACEHOLDER_CONF["hero"]["plugins"])
        self.assertIsNotNone(plugin_pool.get_plugin("TextLinkPlugin"))

    def test_layout_plugins_are_allowed_in_general_editable_content(self):
        allowed = settings.CMS_PLACEHOLDER_CONF["content"]["plugins"]
        for plugin_name in settings.CMS_LAYOUT_PLUGINS:
            with self.subTest(plugin=plugin_name):
                self.assertIn(plugin_name, allowed)

    def test_dynamic_plugins_are_confined_and_limited_to_dedicated_slots(self):
        dedicated = {
            "HeroContentPlugin": "hero",
            "FeatureGridPlugin": "features",
            "FAQListPlugin": "about",
            "LiveProductGridPlugin": "products",
            "LivePricingGridPlugin": "pricing",
            "LiveReleaseListPlugin": "releases",
            "LiveBlogListPlugin": "blog",
        }
        generic_plugins = settings.CMS_PLACEHOLDER_CONF["content"]["plugins"]
        for plugin_name, slot in dedicated.items():
            with self.subTest(plugin=plugin_name):
                plugin_class = plugin_pool.get_plugin(plugin_name)
                self.assertEqual(plugin_class.allowed_slots, [slot])
                self.assertIn(plugin_name, settings.CMS_PLACEHOLDER_CONF[slot]["plugins"])
                self.assertEqual(settings.CMS_PLACEHOLDER_CONF[slot]["limits"][plugin_name], 1)
                self.assertNotIn(plugin_name, generic_plugins)

    def test_homepage_has_a_dedicated_live_blog_placeholder(self):
        self.assertIn("blog", settings.CMS_PLACEHOLDER_CONF)
        self.assertIn("LiveBlogListPlugin", settings.CMS_PLACEHOLDER_CONF["blog"]["plugins"])

    def test_dynamic_plugin_templates_compile(self):
        for template_name in (
            "portal/plugins/hero_content.html",
            "portal/plugins/feature_grid.html",
            "portal/plugins/faq_list.html",
            "portal/plugins/live_products.html",
            "portal/plugins/live_pricing.html",
            "portal/plugins/live_releases.html",
            "portal/plugins/live_blog.html",
            "portal/plugins/external_image.html",
            "portal/plugins/uploaded_image.html",
        ):
            self.assertIsNotNone(get_template(template_name))

    def test_cms_plugin_models_match_the_committed_portal_migrations(self):
        models = (
            CMSExternalImage,
            CMSUploadedImage,
            CMSHeroContent,
            CMSFeatureGrid,
            CMSFAQList,
        )
        for model in models:
            self.assertEqual(model._meta.app_label, "portal")
        loader = MigrationLoader(None)
        self.assertIn(("portal", "0001_initial"), loader.disk_migrations)
        self.assertIn(("portal", "0002_structured_homepage_plugins"), loader.disk_migrations)

        migrated_apps = loader.project_state().apps
        for model in models:
            with self.subTest(model=model.__name__):
                migrated_model = migrated_apps.get_model("portal", model.__name__)
                current_fields = {
                    field.name: field
                    for field in model._meta.local_fields
                }
                migrated_fields = {
                    field.name: field
                    for field in migrated_model._meta.local_fields
                }
                self.assertEqual(set(current_fields), set(migrated_fields))

                # Compare the schema-relevant values of both the legacy
                # auto-created links and the explicit namespaced plugin links.
                schema_attributes = (
                    "max_length",
                    "blank",
                    "null",
                    "primary_key",
                    "parent_link",
                    "upload_to",
                    "verbose_name",
                    "help_text",
                    "validators",
                )
                for field_name, current_field in current_fields.items():
                    migrated_field = migrated_fields[field_name]
                    with self.subTest(field=field_name):
                        self.assertEqual(
                            current_field.get_internal_type(),
                            migrated_field.get_internal_type(),
                        )
                        for attribute in schema_attributes:
                            if hasattr(current_field, attribute) or hasattr(migrated_field, attribute):
                                self.assertEqual(
                                    getattr(current_field, attribute, None),
                                    getattr(migrated_field, attribute, None),
                                    f"{model.__name__}.{field_name}.{attribute} differs",
                                )
                        if current_field.is_relation:
                            self.assertEqual(
                                current_field.remote_field.model._meta.label_lower,
                                migrated_field.remote_field.model._meta.label_lower,
                            )

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
        for slot, plugin_type in (
            ("hero", "HeroContentPlugin"),
            ("features", "FeatureGridPlugin"),
            ("about", "FAQListPlugin"),
            ("products", "LiveProductGridPlugin"),
            ("releases", "LiveReleaseListPlugin"),
            ("blog", "LiveBlogListPlugin"),
        ):
            with self.subTest(slot=slot):
                self.assertTrue(
                    CMSPlugin.objects.filter(
                        placeholder=placeholders[slot],
                        language="fa",
                        plugin_type=plugin_type,
                    ).exists()
                )

        # Simulate an existing homepage created before the blog slot existed.
        # Bootstrap must rescan the changed template and recreate the missing
        # slot without replacing unrelated content.
        page_content = root_url.page.pagecontent_set.get(language="fa")
        placeholders["blog"].delete()
        call_command("bootstrap_cms_homepage", verbosity=0)
        placeholders = {
            placeholder.slot: placeholder
            for placeholder in Placeholder.objects.get_for_obj(page_content)
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

        rendered = response.content.decode()
        self.assertNotIn('id="pricing"', rendered)
        self.assertNotContains(response, "طرح مناسب خودتان را انتخاب کنید")
        for section_id in ("products", "releases", "blog"):
            with self.subTest(section=section_id):
                self.assertEqual(
                    rendered.count(f'id="{section_id}"'),
                    1,
                    f"CMS section '{section_id}' must not be nested or duplicated.",
                )

    def test_legacy_homepage_sections_convert_without_losing_original_html(self):
        from portal.models import CMSFAQList, CMSFeatureGrid, CMSHeroContent

        call_command("bootstrap_cms_homepage", verbosity=0)
        root_url = PageUrl.objects.filter(
            site=self.site, language="fa", path__in=("", "/")
        ).select_related("page").first()
        page_content = root_url.page.pagecontent_set.get(language="fa")
        placeholders = {
            placeholder.slot: placeholder
            for placeholder in Placeholder.objects.get_for_obj(page_content)
        }
        legacy_content = {
            "hero": (
                "TextPlugin",
                '<p>فضای دیجیتال شما، با نظم تازه</p>'
                '<h1>همه‌چیز سر جای خودش؛<br>کنترل در دست شما...</h1>'
                '<p>توضیحی که باید حفظ شود.</p>'
                '<p><a href="/products/">کشف محصولات</a>'
                '<a href="/pricing/">تعرفه‌ها</a></p>'
                '<p>حساب امن◇خرید یکپارچه⌁تجربه هماهنگ</p>',
            ),
            "features": (
                "TextPlugin",
                '<div class="nv-feature-grid"><article class="nv-feature-card">'
                '<span class="nv-feature-icon">⌘</span><span class="nv-feature-number">01</span>'
                '<h3>پیشخوان متمرکز</h3><p>توضیح کارت</p>'
                '<a href="/dashboard/">رفتن به پیشخوان ↗</a></article></div>',
            ),
            "about": (
                "TextPlugin",
                '<div class="nv-faq-list"><details><summary>پرسش آزمایشی؟'
                '<span>＋</span></summary><p>پاسخ آزمایشی.</p></details></div>',
            ),
        }
        for slot, (plugin_type, body) in legacy_content.items():
            CMSPlugin.objects.filter(
                placeholder=placeholders[slot], language="fa"
            ).delete()
            add_plugin(placeholders[slot], plugin_type, "fa", body=body)

        call_command("bootstrap_cms_homepage", verbosity=0)

        for slot, plugin_type in (
            ("hero", "HeroContentPlugin"),
            ("features", "FeatureGridPlugin"),
            ("about", "FAQListPlugin"),
        ):
            with self.subTest(slot=slot):
                plugins = CMSPlugin.objects.filter(
                    placeholder=placeholders[slot],
                    language="fa",
                    plugin_type=plugin_type,
                    parent__isnull=True,
                )
                self.assertEqual(plugins.count(), 1)
                self.assertEqual(
                    CMSPlugin.objects.filter(
                        placeholder=placeholders[slot],
                        language="fa",
                        parent__isnull=True,
                    ).count(),
                    1,
                )

        hero = CMSHeroContent.objects.get(
            cmsplugin_ptr_id=CMSPlugin.objects.get(
                placeholder=placeholders["hero"], plugin_type="HeroContentPlugin"
            ).pk
        )
        self.assertEqual(hero.heading, "همه‌چیز سر جای خودش؛")
        self.assertEqual(hero.heading_accent, "کنترل در دست شما...")
        self.assertEqual(hero.description, "توضیحی که باید حفظ شود.")
        self.assertEqual(hero.primary_cta_url, "/products/")
        self.assertEqual(hero.legacy_source, legacy_content["hero"][1])

        feature = CMSFeatureGrid.objects.get(
            cmsplugin_ptr_id=CMSPlugin.objects.get(
                placeholder=placeholders["features"], plugin_type="FeatureGridPlugin"
            ).pk
        )
        self.assertEqual(feature.feature_1_title, "پیشخوان متمرکز")
        self.assertEqual(feature.feature_1_description, "توضیح کارت")
        self.assertEqual(feature.legacy_source, legacy_content["features"][1])

        faq = CMSFAQList.objects.get(
            cmsplugin_ptr_id=CMSPlugin.objects.get(
                placeholder=placeholders["about"], plugin_type="FAQListPlugin"
            ).pk
        )
        self.assertEqual(faq.question_1, "پرسش آزمایشی؟")
        self.assertEqual(faq.answer_1, "پاسخ آزمایشی.")
        self.assertEqual(faq.legacy_source, legacy_content["about"][1])

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="gradient-text"', html=False)
        self.assertContains(response, "nv-feature-grid", html=False)
        self.assertContains(response, "nv-faq-list", html=False)
        self.assertContains(response, "توضیحی که باید حفظ شود.")

        plugin_ids = {
            slot: CMSPlugin.objects.get(
                placeholder=placeholders[slot],
                language="fa",
                plugin_type=plugin_type,
            ).pk
            for slot, plugin_type in (
                ("hero", "HeroContentPlugin"),
                ("features", "FeatureGridPlugin"),
                ("about", "FAQListPlugin"),
            )
        }
        call_command("bootstrap_cms_homepage", verbosity=0)
        for slot, plugin_id in plugin_ids.items():
            self.assertTrue(CMSPlugin.objects.filter(pk=plugin_id, placeholder=placeholders[slot]).exists())

    def test_bootstrap_failure_rolls_back_template_change(self):
        call_command("bootstrap_cms_homepage", verbosity=0)
        root_url = PageUrl.objects.filter(
            site=self.site,
            language="fa",
            path__in=("", "/"),
        ).select_related("page").first()
        self.assertIsNotNone(root_url)

        page_content = root_url.page.pagecontent_set.get(language="fa")
        page_content.template = "portal/cms_page.html"
        page_content.save(update_fields=["template"])

        with patch(
            "portal.management.commands.bootstrap_cms_homepage.rescan_placeholders_for_obj",
            return_value={},
        ):
            with self.assertRaises(CommandError):
                call_command("bootstrap_cms_homepage", verbosity=0)

        page_content.refresh_from_db()
        self.assertEqual(page_content.template, "portal/cms_page.html")

    def test_one_time_seed_migration_fills_only_empty_hero_and_products_regions(self):
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

        # Reproduce the two empty production slots while leaving all other
        # editor-authored regions intact.
        for slot in ("hero", "products"):
            CMSPlugin.objects.filter(
                placeholder=placeholders[slot],
                language="fa",
            ).delete()

        unchanged_ids = {
            slot: list(
                CMSPlugin.objects.filter(
                    placeholder=placeholders[slot],
                    language="fa",
                ).values_list("pk", flat=True)
            )
            for slot in ("features", "releases", "blog", "about")
        }

        migration = import_module(
            "cms_site_seed.migrations.0001_seed_empty_homepage_regions"
        )
        migration.seed_empty_homepage_regions(None, None)

        self.assertTrue(
            CMSPlugin.objects.filter(
                placeholder=placeholders["hero"],
                language="fa",
                plugin_type="TextPlugin",
            ).exists()
        )
        self.assertTrue(
            CMSPlugin.objects.filter(
                placeholder=placeholders["products"],
                language="fa",
                plugin_type="LiveProductGridPlugin",
            ).exists()
        )
        for slot, original_ids in unchanged_ids.items():
            with self.subTest(slot=slot):
                self.assertEqual(
                    list(
                        CMSPlugin.objects.filter(
                            placeholder=placeholders[slot],
                            language="fa",
                        ).values_list("pk", flat=True)
                    ),
                    original_ids,
                )

        # The migration is safe to call again and cannot create duplicates.
        migration.seed_empty_homepage_regions(None, None)
        self.assertEqual(
            CMSPlugin.objects.filter(
                placeholder=placeholders["hero"],
                language="fa",
            ).count(),
            1,
        )
        self.assertEqual(
            CMSPlugin.objects.filter(
                placeholder=placeholders["products"],
                language="fa",
            ).count(),
            1,
        )

    def test_native_mptree_backend_creates_and_reads_child_pages(self):
        call_command("bootstrap_cms_homepage", verbosity=0)
        root_url = PageUrl.objects.filter(
            site=self.site,
            language="fa",
            path__in=("", "/"),
        ).select_related("page").first()
        child = create_page(
            title="صفحهٔ آزمایشی CMS",
            template="portal/cms_page.html",
            language="fa",
            slug="cms-tree-test",
            parent=root_url.page,
            site=self.site,
            created_by="cms-tree-test",
        )
        self.assertEqual(child.parent_id, root_url.page.pk)
        self.assertEqual(child.depth, root_url.page.depth + 1)
        self.assertTrue(child.path.startswith(root_url.page.path))

    def test_staff_user_receives_the_frontend_cms_toolbar_on_homepage(self):
        call_command("bootstrap_cms_homepage", verbosity=0)
        staff = get_user_model().objects.create_user(
            username="cms_editor",
            password="cms-editor-test-password",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(
            staff,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertContains(response, "cms-toolbar")

    def test_live_product_grid_counts_only_active_plans(self):
        product = Product.objects.create(
            name="CMS test product",
            slug="cms-test-product",
            description="Product rendered from the CMS plugin.",
        )
        plan_fields = {
            "product": product,
            "duration_unit": Plan.DurationUnit.MONTHS,
            "duration_value": 1,
            "price_minor_units": 1000,
            "currency": "IRR",
            "device_limit": 1,
        }
        Plan.objects.create(name="Active plan", slug="active-plan", **plan_fields)
        Plan.objects.create(
            name="Inactive plan",
            slug="inactive-plan",
            is_active=False,
            **plan_fields,
        )

        call_command("bootstrap_cms_homepage", verbosity=0)
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, product.name)
        self.assertContains(response, "1 طرح")
        self.assertNotContains(response, "2 طرح")

    def test_bootstrap_never_overwrites_or_deletes_editor_authored_content(self):
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

        # Existing CMS edits retain their visual hooks and must never be reset.
        feature_plugin = CMSPlugin.objects.get(
            placeholder=placeholders["features"],
            language="fa",
            plugin_type="FeatureGridPlugin",
        )
        feature_instance, _plugin_class = feature_plugin.get_plugin_instance()
        feature_instance.feature_1_description += " EDITOR_FEATURE_CHANGE_SURVIVES"
        feature_instance.save(update_fields=["feature_1_description"])

        faq_plugin = CMSPlugin.objects.get(
            placeholder=placeholders["about"],
            language="fa",
            plugin_type="FAQListPlugin",
        )
        faq_instance, _plugin_class = faq_plugin.get_plugin_instance()
        faq_instance.answer_1 += " EDITOR_FAQ_CHANGE_SURVIVES"
        faq_instance.save(update_fields=["answer_1"])

        # Content that resembles the former seed signatures is still editor-owned.
        generic = placeholders["content"]
        generic_bodies = (
            '<div class="nv-hero-copy"><h1>custom hero</h1></div>',
            '<div class="nv-feature-grid"><article>custom feature</article></div>',
            '<div class="nv-faq-list"><details>custom FAQ</details></div>',
        )
        for body in generic_bodies:
            add_plugin(generic, "TextPlugin", "fa", body=body)

        call_command("bootstrap_cms_homepage", verbosity=0)

        remaining = CMSPlugin.objects.filter(
            placeholder=generic,
            language="fa",
            plugin_type="TextPlugin",
            parent__isnull=True,
        )
        self.assertEqual(remaining.count(), len(generic_bodies))
        for plugin in remaining:
            instance, _plugin_class = plugin.get_plugin_instance()
            self.assertTrue(any(body.strip() in instance.body for body in generic_bodies))

        feature_plugin = CMSPlugin.objects.get(
            placeholder=placeholders["features"],
            language="fa",
            plugin_type="FeatureGridPlugin",
        )
        feature_instance, _plugin_class = feature_plugin.get_plugin_instance()
        self.assertIn("EDITOR_FEATURE_CHANGE_SURVIVES", feature_instance.feature_1_description)

        faq_plugin = CMSPlugin.objects.get(
            placeholder=placeholders["about"],
            language="fa",
            plugin_type="FAQListPlugin",
        )
        faq_instance, _plugin_class = faq_plugin.get_plugin_instance()
        self.assertIn("EDITOR_FAQ_CHANGE_SURVIVES", faq_instance.answer_1)

    def test_storefront_fallback_is_preserved_without_a_cms_homepage(self):
        from cms.models import Page

        Page.objects.filter(site=self.site).delete()
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "کنترل در دست شما")

    def test_authenticated_customer_can_open_cms_homepage(self):
        call_command("bootstrap_cms_homepage", verbosity=0)
        from accounts.models import Customer

        customer = Customer.objects.create_user(
            username="cms_customer",
            email="cms_customer@example.com",
            password="cms-customer-test-password",
        )
        self.client.force_login(
            customer,
            backend="accounts.backends.CustomerAuthenticationBackend",
        )
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "کنترل در دست شما")

    def test_customer_has_perms_api_denies_all_permissions(self):
        from accounts.models import Customer

        customer = Customer.objects.create_user(
            username="permission_customer",
            email="permission_customer@example.com",
            password="customer-test-password",
        )
        self.assertFalse(customer.has_perm("cms.change_page"))
        self.assertFalse(customer.has_perms(["cms.change_page", "cms.add_page"]))
