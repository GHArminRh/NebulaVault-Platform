from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group, Permission
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.middleware import SessionMiddleware

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
        self.assertContains(response, "زیرعنوان برند")
        self.assertContains(response, 'href="/header-test/"')
        self.assertContains(response, "پیوند سربرگ آزمایشی")
        self.assertContains(response, "توضیحات پابرگ آزمایشی")
        self.assertContains(response, "یادداشت پابرگ آزمایشی")
        self.assertContains(response, "© متن حق نشر آزمایشی")
        self.assertContains(response, 'href="/footer-test/"')
        self.assertContains(response, "پیوند پابرگ آزمایشی")
        self.assertNotContains(response, 'id="nv-install-app"')
