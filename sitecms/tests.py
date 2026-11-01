from django.conf import settings
from django.db import connection
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group, Permission
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.contenttypes.models import ContentType
from unittest.mock import patch

from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from accounts.backends import WagtailGroupPermissionsBackend
from wagtail.documents import get_document_model
from wagtail.images import get_image_model
from wagtail.models import (
    Collection,
    GroupCollectionPermission,
    GroupPagePermission,
    Locale,
    Page,
    Site,
)

from .forms import CMSUserCreationForm, CMSUserEditForm
from .models import ContentPage, HomePage, SiteChromeSettings
from .storage_config import build_default_media_storage_config
from django.core.exceptions import ImproperlyConfigured
from .viewsets import CMSUserFilterSet
from .permissions import (
    StaffCollectionManagementPermissionPolicy,
    StaffCollectionOwnershipPermissionPolicy,
    StaffPagePermissionPolicy,
)
from wagtail.permissions import policy_registry


class WagtailIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # config.test_settings disables migrations and syncs the live model
        # schema. Build the minimal Wagtail tree that the production data
        # migration creates so these tests exercise the same homepage lookup.
        if HomePage.objects.exists():
            return

        Locale.objects.get_or_create(language_code=settings.LANGUAGE_CODE)
        page_type = ContentType.objects.get_for_model(Page, for_concrete_model=False)
        home_type = ContentType.objects.get_for_model(HomePage, for_concrete_model=False)
        Page.objects.create(
            title="Root",
            slug="root",
            path="0001",
            depth=1,
            numchild=1,
            url_path="/",
            content_type=page_type,
        )
        base_home = Page.objects.create(
            title="صفحه اصلی نبیولا والت",
            slug="home",
            path="00010001",
            depth=2,
            numchild=0,
            url_path="/home/",
            content_type=home_type,
        )
        # Avoid a multi-table save rewriting the existing Page parent row.
        # This test uses config.test_settings (migrations disabled), so mirror
        # the production data migration's child-table insert.
        quote_name = connection.ops.quote_name
        child_table = quote_name(HomePage._meta.db_table)
        child_fields = [
            ("page_ptr", base_home.pk),
            ("hero_eyebrow", "متن بالای عنوان"),
            ("hero_title", "عنوان قابل ویرایش از Wagtail"),
            ("hero_highlight", "تأکید قابل ویرایش"),
            ("hero_description", "توضیحات قابل ویرایش"),
            ("hero_primary_cta_label", "کشف محصولات"),
            ("hero_primary_cta_url", "#products"),
            ("sections", "[]"),
            ("body", ""),
        ]
        columns = [
            quote_name(HomePage._meta.get_field(name).column)
            for name, _ in child_fields
        ]
        placeholders = ", ".join(["%s"] * len(child_fields))
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {child_table} ({', '.join(columns)}) "
                f"VALUES ({placeholders})",
                [value for _, value in child_fields],
            )
        homepage = HomePage.objects.get(pk=base_home.pk)
        Site.objects.create(
            hostname="testserver",
            port=80,
            is_default_site=True,
            root_page=homepage,
        )

    def test_homepage_wagtail_preview_renders_all_editorial_fields(self):
        homepage = HomePage.objects.get(slug="home")
        homepage.sections = [("heading", "عنوان بخش پیش‌نمایش")]
        homepage.body = "<p>متن تکمیلی پیش‌نمایش</p>"
        homepage.save()

        request = RequestFactory().get("/")
        SessionMiddleware(lambda current_request: None).process_request(request)
        request.user = AnonymousUser()
        request._messages = FallbackStorage(request)

        rendered = render_to_string(
            "sitecms/home_page.html",
            {
                "page": homepage,
                "products": [],
                "releases": [],
                "latest_blog_posts": [],
            },
            request=request,
        )

        self.assertIn(homepage.hero_eyebrow, rendered)
        self.assertIn(homepage.hero_title, rendered)
        self.assertIn(homepage.hero_highlight, rendered)
        self.assertIn(homepage.hero_description, rendered)
        self.assertIn(homepage.hero_primary_cta_label, rendered)
        self.assertIn("عنوان بخش پیش‌نمایش", rendered)
        self.assertIn("متن تکمیلی پیش‌نمایش", rendered)

    def test_streamfield_blocks_render_on_editorial_pages(self):
        homepage = HomePage.objects.get(slug="home")
        content_page = ContentPage(
            title="صفحه بلوک‌های آزمایشی",
            slug="cms-blocks-test",
            sections=[
                ("heading", "عنوان بلوک آزمایشی"),
                ("rich_text", "<p>متن بلوک آزمایشی</p>"),
                ("notice", {
                    "title": "اطلاعیه آزمایشی",
                    "text": "متن اطلاعیه",
                    "tone": "info",
                }),
            ],
        )
        homepage.add_child(instance=content_page)
        content_page.save_revision().publish()

        response = self.client.get("/cms-blocks-test/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "عنوان بلوک آزمایشی")
        self.assertContains(response, "متن بلوک آزمایشی")
        self.assertContains(response, "اطلاعیه آزمایشی")

    def test_wagtail_sitemap_route_is_available(self):
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/xml", response["Content-Type"])

    def test_object_storage_configuration_fails_closed(self):
        local = build_default_media_storage_config(backend="local")
        self.assertEqual(
            local["BACKEND"],
            "django.core.files.storage.FileSystemStorage",
        )
        with self.assertRaises(ImproperlyConfigured):
            build_default_media_storage_config(
                backend="s3",
                bucket_name="nebula-vault-media-2026",
                access_key="test-key",
                secret_key="test-secret",
                region_name="us-east-005",
                endpoint_url="",
            )
        with self.assertRaises(ImproperlyConfigured):
            build_default_media_storage_config(backend="unknown")

        configured = build_default_media_storage_config(
            backend="s3",
            bucket_name="private-bucket",
            access_key="test-key",
            secret_key="test-secret",
            region_name="us-east-005",
            endpoint_url="https://s3.us-east-005.backblazeb2.com",
        )
        self.assertEqual(
            configured["BACKEND"],
            "sitecms.storage.PrivateMediaS3Storage",
        )
        self.assertIsNone(configured["OPTIONS"]["default_acl"])

    def test_site_chrome_settings_control_header_and_footer(self):
        site = Site.objects.get(is_default_site=True)
        chrome = SiteChromeSettings.for_site(site)
        chrome.brand_title = "برند قابل ویرایش"
        chrome.brand_subtitle = "زیرعنوان قابل ویرایش"
        chrome.header_links = [
            (
                "link",
                {
                    "label": "پیوند سربرگ آزمایشی",
                    "url": "/header-test/",
                    "open_in_new_tab": False,
                },
            )
        ]
        chrome.footer_description = "توضیحات پابرگ آزمایشی"
        chrome.footer_note = "یادداشت پابرگ آزمایشی"
        chrome.footer_copyright = "© متن حق نشر آزمایشی"
        chrome.footer_links = [
            (
                "link",
                {
                    "label": "پیوند پابرگ آزمایشی",
                    "url": "/footer-test/",
                    "open_in_new_tab": False,
                },
            )
        ]
        chrome.show_install_button = False
        chrome.save()

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "برند قابل ویرایش")
        self.assertContains(response, "زیرعنوان قابل ویرایش")
        self.assertContains(response, 'href="/header-test/"')
        self.assertContains(response, "پیوند سربرگ آزمایشی")
        self.assertContains(response, "توضیحات پابرگ آزمایشی")
        self.assertContains(response, "یادداشت پابرگ آزمایشی")
        self.assertContains(response, "© متن حق نشر آزمایشی")
        self.assertContains(response, 'href="/footer-test/"')
        self.assertContains(response, "پیوند پابرگ آزمایشی")
        self.assertNotContains(response, 'id="nv-install-app"')

    def test_homepage_feature_faq_and_proof_sections_are_editorial(self):
        homepage = HomePage.objects.get(slug="home")
        homepage.sections = [
            (
                "proof_strip",
                {
                    "title": "اعتماد و یکپارچگی",
                    "items": [{"number": "01", "label": "مدیریت یکپارچه"}],
                },
            ),
            (
                "product_listing",
                {
                    "eyebrow": "محصولات آزمایشی",
                    "title": "فهرست محصولات قابل ویرایش",
                    "description": "توضیح محصولات",
                },
            ),
            (
                "feature_grid",
                {
                    "eyebrow": "ویژگی آزمایشی",
                    "title": "عنوان ویژگی قابل ویرایش",
                    "description": "توضیحات ویژگی",
                    "items": [
                        {
                            "icon": "◇",
                            "title": "کارت قابل ویرایش",
                            "text": "توضیحات کارت",
                            "link_label": "مشاهده",
                            "link_url": "#products",
                        }
                    ],
                },
            ),
            (
                "blog_listing",
                {
                    "eyebrow": "بلاگ آزمایشی",
                    "title": "فهرست بلاگ قابل ویرایش",
                    "description": "توضیح بلاگ",
                    "link_label": "همه نوشته‌ها",
                },
            ),
            (
                "release_listing",
                {
                    "eyebrow": "نسخه‌های آزمایشی",
                    "title": "فهرست نسخه‌های قابل ویرایش",
                    "description": "توضیح نسخه‌ها",
                },
            ),
            (
                "faq",
                {
                    "eyebrow": "پرسش آزمایشی",
                    "title": "پرسش‌های قابل ویرایش",
                    "description": "توضیح پرسش‌ها",
                    "items": [
                        {
                            "question": "پرسش از CMS؟",
                            "answer": "بله؛ پاسخ از CMS مدیریت می‌شود.",
                        }
                    ],
                },
            ),
            (
                "call_to_action",
                {
                    "eyebrow": "دعوت آزمایشی",
                    "title": "دعوت قابل ویرایش",
                    "text": "متن دعوت",
                    "button_label": "شروع",
                    "button_url": "/accounts/register/",
                },
            ),
        ]
        homepage.save()

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "فهرست محصولات قابل ویرایش")
        self.assertContains(response, "فهرست بلاگ قابل ویرایش")
        self.assertContains(response, "فهرست نسخه‌های قابل ویرایش")
        self.assertContains(response, "عنوان ویژگی قابل ویرایش")
        self.assertContains(response, "کارت قابل ویرایش")
        self.assertContains(response, "پرسش‌های قابل ویرایش")
        self.assertContains(response, "پرسش از CMS؟")
        self.assertContains(response, "اعتماد و یکپارچگی")
        self.assertContains(response, "دعوت قابل ویرایش")

    def test_existing_storefront_homepage_is_managed_by_wagtail(self):
        homepage = HomePage.objects.get(slug="home")
        self.assertEqual(
            Site.objects.get(is_default_site=True).root_page_id,
            homepage.pk,
        )

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, homepage.hero_title)
        self.assertContains(response, homepage.hero_highlight)
        self.assertContains(response, '<meta property="og:type" content="website">')

    def test_published_wagtail_content_page_uses_canonical_root_url(self):
        homepage = HomePage.objects.get(slug="home")
        content_page = ContentPage(
            title="صفحه راهنمای آزمایشی",
            slug="cms-guide-test",
            intro="معرفی صفحه",
            body="<p>محتوای منتشرشده</p>",
        )
        homepage.add_child(instance=content_page)
        content_page.save_revision().publish()

        response = self.client.get("/cms-guide-test/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "صفحه راهنمای آزمایشی")
        self.assertEqual(content_page.get_url(), "/cms-guide-test/")

    def test_project_permission_policies_are_registered_for_wagtail(self):
        self.assertIsInstance(
            policy_registry.get_by_type(Page), StaffPagePermissionPolicy
        )
        self.assertIsInstance(
            policy_registry.get_by_type(Collection), StaffCollectionManagementPermissionPolicy
        )
        self.assertIsInstance(
            policy_registry.get_by_type(get_image_model()),
            StaffCollectionOwnershipPermissionPolicy,
        )
        self.assertIsInstance(
            policy_registry.get_by_type(get_document_model()),
            StaffCollectionOwnershipPermissionPolicy,
        )

    def test_active_staff_superuser_can_open_homepage_editor(self):
        User = get_user_model()
        admin_user = User.objects.create_superuser(
            username="wagtail-admin",
            email="wagtail-admin@example.invalid",
            password="test-password-only",
        )
        self.client.force_login(
            admin_user, backend="django.contrib.auth.backends.ModelBackend"
        )

        homepage = HomePage.objects.get(slug="home")
        response = self.client.get(
            reverse("wagtailadmin_pages:edit", args=(homepage.pk,))
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "hero_title")
        self.assertContains(response, "hero_description")

    def test_wagtail_admin_login_uses_the_django_admin_login(self):
        response = self.client.get(
            "/cms/login/?next=%2Fcms%2Fpages%2F2%2Fedit%2F"
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            "/admin/login/?next=%2Fcms%2Fpages%2F2%2Fedit%2F",
        )

        login_response = self.client.get(response["Location"])
        self.assertEqual(login_response.status_code, 200)
        self.assertContains(login_response, 'id="login-form"')
        self.assertContains(login_response, "Security verification")
        self.assertEqual(
            login_response.context["form"].__class__.__name__,
            "AdminTurnstileAuthenticationForm",
        )

    def test_cms_login_rejects_external_next_redirects(self):
        response = self.client.get(
            "/cms/login/?next=https%3A%2F%2Fevil.example%2F"
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            "/admin/login/?next=%2Fcms%2F",
        )

    def test_staff_users_can_be_assigned_wagtail_groups(self):
        creation_form = CMSUserCreationForm()
        edit_form = CMSUserEditForm()
        self.assertIn("wagtail_groups", creation_form.fields)
        self.assertIn("wagtail_groups", edit_form.fields)
        self.assertTrue(creation_form.fields["is_staff"].initial)
        self.assertIn("is_staff", edit_form.fields)
        self.assertNotIn("is_staff", CMSUserEditForm(editing_self=True).fields)
        self.assertNotIn("groups", creation_form.fields)
        self.assertNotIn("groups", edit_form.fields)
        self.assertEqual(
            CMSUserFilterSet().filters["group"].field_name,
            "wagtail_groups",
        )

    def test_wagtail_group_permissions_use_the_separate_membership(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="cms-editor",
            password="test-password-only",
            is_staff=True,
        )
        group = Group.objects.create(name="CMS Editors")
        user.wagtail_groups.add(group)

        page_content_type = ContentType.objects.get_for_model(Page)
        permission = Permission.objects.get(
            content_type=page_content_type,
            codename="add_page",
        )
        root = Page.objects.get(depth=1)
        root.owner = user
        root.save(update_fields=["owner"])
        GroupPagePermission.objects.create(
            group=group,
            page=root,
            permission=permission,
        )

        self.assertTrue(
            GroupPagePermission.objects.filter(
                group__user=user,
                page=root,
                permission=permission,
            ).exists()
        )
        standard_permission = Permission.objects.get(
            content_type=ContentType.objects.get_for_model(Group),
            codename="view_group",
        )
        group.permissions.add(standard_permission)
        self.assertIn(
            f"{standard_permission.content_type.app_label}.{standard_permission.codename}",
            WagtailGroupPermissionsBackend().get_group_permissions(user),
        )
        page_policy = StaffPagePermissionPolicy()
        self.assertIn(user, page_policy.users_with_any_permission({"add"}))
        self.assertIn(
            user,
            page_policy.users_with_any_permission_for_instance({"change"}, root),
        )

    def test_wagtail_media_collection_permissions_use_wagtail_groups(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="cms-media-editor",
            password="test-password-only",
            is_staff=True,
        )
        group = Group.objects.create(name="CMS Media Editors")
        user.wagtail_groups.add(group)
        root_collection = Collection.add_root(name="CMS Media Root")
        child_collection = root_collection.add_child(name="CMS Images")
        content_type = ContentType.objects.get_for_model(Collection)
        permission, _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename="change_collection",
            defaults={"name": "Can change collection"},
        )
        GroupCollectionPermission.objects.create(
            group=group,
            collection=root_collection,
            permission=permission,
        )
        policy = StaffCollectionManagementPermissionPolicy(Collection)
        self.assertIn(child_collection, policy._descendants_with_perm(user, "change"))
        self.assertIn(
            user,
            policy.users_with_any_permission_for_instance({"change"}, child_collection),
        )

        media_models = (
            (get_image_model(), "add_image"),
            (get_document_model(), "add_document"),
        )
        # Wagtail caches collection permissions on the user instance. Populate
        # every media permission before the first policy lookup, as happens in
        # normal group setup, then verify both policies against that cache.
        for model, action in media_models:
            permission = Permission.objects.get(
                content_type=ContentType.objects.get_for_model(model),
                codename=action,
            )
            GroupCollectionPermission.objects.create(
                group=group,
                collection=root_collection,
                permission=permission,
            )

        for model, action in media_models:
            model_policy = policy_registry.get_by_type(model)
            diagnostic = (
                f"model={model._meta.label_lower}; "
                f"auth_model={model_policy.auth_model._meta.label_lower}; "
                f"authenticated={user.is_authenticated}; active={user.is_active}; "
                f"wagtail_groups={list(user.wagtail_groups.values_list('name', flat=True))}; "
                f"expected_codename={action}; "
                f"policy_codenames={model_policy._get_permission_codenames({'add'})}; "
                f"cached_permissions={list(model_policy.get_cached_permissions_for_user(user))}; "
                f"loaded_permissions={list(model_policy.get_all_permissions_for_user(user).values_list('permission__codename', flat=True))}"
            )
            self.assertTrue(model_policy.user_has_permission(user, "add"), diagnostic)
            self.assertIn(user, model_policy.users_with_any_permission({"add"}))


@override_settings(
    WAGTAIL_CRON_SECRET="test-wagtail-cron-secret-that-is-long-enough-123456"
)
class ScheduledPublishingEndpointTests(TestCase):
    def setUp(self):
        self.url = reverse("wagtail-publish-scheduled")
        self.secret = "test-wagtail-cron-secret-that-is-long-enough-123456"

    @patch("sitecms.cron_views.call_command")
    def test_valid_bearer_secret_runs_wagtail_command(self, mocked_command):
        response = self.client.post(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {self.secret}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        mocked_command.assert_called_once()
        self.assertEqual(mocked_command.call_args.args, ("publish_scheduled",))

    @patch("sitecms.cron_views.call_command")
    def test_invalid_bearer_secret_is_rejected(self, mocked_command):
        response = self.client.post(
            self.url,
            HTTP_AUTHORIZATION="Bearer incorrect-secret",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "unauthorized")
        mocked_command.assert_not_called()

    @override_settings(WAGTAIL_CRON_SECRET="a" * 40 + "رمز-محرمانه")
    @patch("sitecms.cron_views.call_command")
    def test_valid_unicode_bearer_secret_runs_wagtail_command(self, mocked_command):
        from sitecms.cron_views import publish_scheduled_pages

        secret = "a" * 40 + "رمز-محرمانه"
        request = RequestFactory().post(
            self.url,
            HTTP_AUTHORIZATION="Bearer placeholder",
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {secret}"

        response = publish_scheduled_pages(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        mocked_command.assert_called_once()
        self.assertEqual(mocked_command.call_args.args, ("publish_scheduled",))

    @override_settings(WAGTAIL_CRON_SECRET="a" * 40 + "رمز-محرمانه")
    @patch("sitecms.cron_views.call_command")
    def test_invalid_unicode_bearer_secret_returns_forbidden(self, mocked_command):
        from sitecms.cron_views import publish_scheduled_pages

        request = RequestFactory().post(
            self.url,
            HTTP_AUTHORIZATION="Bearer placeholder",
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {'a' * 40}رمز-اشتباه"

        response = publish_scheduled_pages(request)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "unauthorized")
        mocked_command.assert_not_called()

    def test_endpoint_accepts_post_only(self):
        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {self.secret}",
        )

        self.assertEqual(response.status_code, 405)

    @override_settings(WAGTAIL_CRON_SECRET="")
    def test_endpoint_is_disabled_when_secret_is_not_configured(self):
        response = self.client.post(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {self.secret}",
        )

        self.assertEqual(response.status_code, 503)
