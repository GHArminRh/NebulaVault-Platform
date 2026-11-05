from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase

from .models import SEOAuditIssue, SEOAuditRun
from .services.crawler import SiteCrawler


class SEOAuditModelTests(TestCase):
    def test_audit_run_records_requested_by_and_counters(self):
        staff = get_user_model().objects.create_user(
            username="seo-auditor",
            password="test-password",
        )
        run = SEOAuditRun.objects.create(requested_by=staff, pages_scanned=4)

        self.assertEqual(run.status, SEOAuditRun.Status.QUEUED)
        self.assertEqual(run.pages_scanned, 4)
        self.assertEqual(run.requested_by, staff)

    def test_issue_is_unique_per_run_url_and_code(self):
        run = SEOAuditRun.objects.create()
        issue_data = {
            "run": run,
            "url": "https://mydigigi.ir/example/",
            "code": "missing-title",
            "severity": SEOAuditIssue.Severity.ERROR,
            "title": "Page has no title",
        }
        SEOAuditIssue.objects.create(**issue_data)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SEOAuditIssue.objects.create(**issue_data)


class StubFetcher:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def __call__(self, url, accept="text/html"):
        self.calls.append(url)
        status, content_type, body = self.pages.get(
            url, (404, "text/html; charset=utf-8", b"")
        )
        return status, content_type, body, url


class SEOCrawlerTests(SimpleTestCase):
    def test_normalize_url_rejects_external_and_sensitive_routes(self):
        crawler = SiteCrawler(base_url="https://mydigigi.ir", fetcher=lambda *a, **k: None)

        self.assertEqual(
            crawler.normalize_url("/products/nebula/"),
            "https://mydigigi.ir/products/nebula/",
        )
        self.assertIsNone(crawler.normalize_url("https://evil.example/"))
        self.assertIsNone(crawler.normalize_url("/admin/"))
        self.assertIsNone(crawler.normalize_url("/accounts/login/"))
        self.assertIsNone(crawler.normalize_url("/products/?page=2"))

    def test_crawler_reports_missing_metadata_and_follows_same_origin_links(self):
        home = b"""<!doctype html><html><head><title>Home page</title>
        <meta name="description" content="A short description">
        <link rel="canonical" href="https://mydigigi.ir/">
        </head><body><h1>Home</h1><a href="/products/nebula/">Product</a>
        <a href="https://external.example/">External</a></body></html>"""
        product = b"""<!doctype html><html><head></head><body>
        <img src="/image.webp"><h1>Product</h1></body></html>"""
        fetcher = StubFetcher({
            "https://mydigigi.ir/robots.txt": (404, "text/plain", b""),
            "https://mydigigi.ir/sitemap.xml": (404, "application/xml", b""),
            "https://mydigigi.ir/": (200, "text/html; charset=utf-8", home),
            "https://mydigigi.ir/products/nebula/": (200, "text/html; charset=utf-8", product),
        })
        result = SiteCrawler(
            base_url="https://mydigigi.ir",
            fetcher=fetcher,
            max_pages=10,
            request_delay=0,
        ).crawl()

        self.assertEqual(result["pages_scanned"], 2)
        issue_codes = {issue["code"] for issue in result["issues"]}
        self.assertIn("missing-title", issue_codes)
        self.assertIn("missing-meta-description", issue_codes)
        self.assertIn("missing-canonical", issue_codes)
        self.assertIn("images-missing-alt", issue_codes)
        self.assertFalse(any("external.example" in url for url in fetcher.calls))

    def test_robots_disallow_rules_are_respected(self):
        home = b"""<html><head><title>Home</title></head><body>
        <a href="/private-preview/">Private</a><a href="/products/">Products</a>
        </body></html>"""
        fetcher = StubFetcher({
            "https://mydigigi.ir/robots.txt": (
                200, "text/plain", b"User-agent: *\nDisallow: /private-preview/\n"
            ),
            "https://mydigigi.ir/sitemap.xml": (404, "application/xml", b""),
            "https://mydigigi.ir/": (200, "text/html", home),
            "https://mydigigi.ir/products/": (200, "text/html", b"<title>Products</title>"),
        })
        result = SiteCrawler(
            base_url="https://mydigigi.ir",
            fetcher=fetcher,
            request_delay=0,
        ).crawl()

        self.assertEqual(result["pages_scanned"], 2)
        self.assertNotIn("https://mydigigi.ir/private-preview/", fetcher.calls)


class SEOContextProcessorTests(SimpleTestCase):
    def test_private_utility_routes_are_noindex(self):
        from django.test import RequestFactory, override_settings

        from .context_processors import seo_context

        request = RequestFactory().get("/cart/")
        with override_settings(SITE_BASE_URL="https://mydigigi.ir"):
            result = seo_context(request)

        self.assertEqual(result["seo_default_robots"], "noindex,nofollow")
        self.assertEqual(result["seo_canonical_url"], "https://mydigigi.ir/cart/")

    def test_public_product_routes_are_indexable(self):
        from django.test import RequestFactory, override_settings

        from .context_processors import seo_context

        request = RequestFactory().get("/products/nebula/")
        with override_settings(SITE_BASE_URL="https://mydigigi.ir"):
            result = seo_context(request)

        self.assertEqual(result["seo_default_robots"], "index,follow")
        self.assertEqual(
            result["seo_canonical_url"],
            "https://mydigigi.ir/products/nebula/",
        )


class WagtailSitemapEligibilityTests(SimpleTestCase):
    def test_homepage_alone_does_not_make_wagtail_sitemap_eligible(self):
        from unittest.mock import Mock, patch

        from seo.views import _has_public_wagtail_pages

        site = Mock()
        site.root_page.get_descendants.return_value.live.return_value.public.return_value.exists.return_value = False
        with patch("seo.views.Site.objects.filter") as filter_sites:
            filter_sites.return_value.select_related.return_value.first.return_value = site
            self.assertFalse(_has_public_wagtail_pages())

    def test_public_descendant_makes_wagtail_sitemap_eligible(self):
        from unittest.mock import Mock, patch

        from seo.views import _has_public_wagtail_pages

        site = Mock()
        site.root_page.get_descendants.return_value.live.return_value.public.return_value.exists.return_value = True
        with patch("seo.views.Site.objects.filter") as filter_sites:
            filter_sites.return_value.select_related.return_value.first.return_value = site
            self.assertTrue(_has_public_wagtail_pages())

    def test_missing_default_wagtail_site_is_not_eligible(self):
        from unittest.mock import patch

        from seo.views import _has_public_wagtail_pages

        with patch("seo.views.Site.objects.filter") as filter_sites:
            filter_sites.return_value.select_related.return_value.first.return_value = None
            self.assertFalse(_has_public_wagtail_pages())


class SEORobotsAndSitemapTests(TestCase):
    def test_robots_txt_blocks_private_routes_and_advertises_sitemap(self):
        from django.test import override_settings

        with override_settings(SITE_BASE_URL="https://mydigigi.ir"):
            response = self.client.get("/robots.txt")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Disallow: /admin/")
        self.assertContains(response, "Disallow: /cart/")
        self.assertContains(response, "Sitemap: https://mydigigi.ir/sitemap.xml")

    def _sitemap_locations(self, response):
        from xml.etree import ElementTree

        self.assertEqual(response.status_code, 200)
        root = ElementTree.fromstring(response.content)
        return [
            node.text
            for node in root.iter()
            if node.tag.endswith("loc")
        ]

    def test_sitemap_index_omits_wagtail_when_it_has_no_public_pages(self):
        from unittest.mock import patch
        from django.test import override_settings

        with (
            override_settings(SITE_BASE_URL="https://mydigigi.ir"),
            patch("seo.views._has_public_wagtail_pages", return_value=False),
        ):
            response = self.client.get("/sitemap.xml")

        locations = self._sitemap_locations(response)
        self.assertIn("https://mydigigi.ir/sitemap-pages.xml", locations)
        self.assertIn("https://mydigigi.ir/sitemap-products.xml", locations)
        self.assertIn("https://mydigigi.ir/sitemap-blog.xml", locations)
        self.assertNotIn("https://mydigigi.ir/sitemap-wagtail.xml", locations)

    def test_sitemap_index_includes_wagtail_when_public_pages_exist(self):
        from unittest.mock import patch
        from django.test import override_settings

        with (
            override_settings(SITE_BASE_URL="https://mydigigi.ir"),
            patch("seo.views._has_public_wagtail_pages", return_value=True),
        ):
            response = self.client.get("/sitemap.xml")

        locations = self._sitemap_locations(response)
        self.assertIn("https://mydigigi.ir/sitemap-wagtail.xml", locations)


class SEODashboardTests(TestCase):
    def test_staff_admin_can_view_dashboard_and_latest_findings(self):
        staff = get_user_model().objects.create_superuser(
            username="seo-admin",
            email="seo-admin@example.invalid",
            password="test-password",
        )
        # force_login defaults to the first configured backend, which is the
        # customer-only backend in this project. Exercise the actual staff
        # permission backend for this Django admin view instead.
        self.client.force_login(
            staff,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        run = SEOAuditRun.objects.create(pages_scanned=3, issues_count=1)
        SEOAuditIssue.objects.create(
            run=run,
            url="https://mydigigi.ir/products/example/",
            code="missing-title",
            severity=SEOAuditIssue.Severity.ERROR,
            title="Page has no title",
            recommendation="Add a unique title.",
        )

        response = self.client.get("/admin/seo-center/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nebula SEO Center")
        self.assertContains(response, "Page has no title")
        self.assertContains(response, "Add a unique title.")

        changelist = self.client.get("/admin/seo/seoauditrun/")
        self.assertEqual(changelist.status_code, 200)
        self.assertContains(changelist, "SEO Center dashboard")

    def test_admin_app_index_links_directly_to_seo_center_dashboard(self):
        staff = get_user_model().objects.create_superuser(
            username="seo-index-admin",
            email="seo-index-admin@example.invalid",
            password="test-password",
        )
        self.client.force_login(
            staff,
            backend="django.contrib.auth.backends.ModelBackend",
        )

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SEO Center dashboard")
        self.assertContains(response, 'href="/admin/seo-center/"')


class SearchConsoleHelperTests(SimpleTestCase):
    def test_refresh_token_is_encrypted_and_round_trips(self):
        from django.test import override_settings

        from .search_console import decrypt_refresh_token, encrypt_refresh_token

        with override_settings(SECRET_KEY="test-secret-key-for-search-console"):
            encrypted = encrypt_refresh_token("google-refresh-token")
            self.assertNotEqual(encrypted, "google-refresh-token")
            self.assertEqual(decrypt_refresh_token(encrypted), "google-refresh-token")

    def test_search_console_property_validation(self):
        from .search_console_views import _valid_property

        self.assertTrue(_valid_property("https://mydigigi.ir/"))
        self.assertTrue(_valid_property("https://mydigigi.ir"))
        self.assertTrue(_valid_property("sc-domain:mydigigi.ir"))
        self.assertFalse(_valid_property("http://mydigigi.ir/"))
        self.assertFalse(_valid_property("https://mydigigi.ir/path/"))
        self.assertFalse(_valid_property("https://user:pass@mydigigi.ir/"))
        self.assertFalse(_valid_property("https://mydigigi.ir:invalid/"))
        self.assertFalse(_valid_property("https://[::1/"))
        self.assertFalse(_valid_property("sc-domain:localhost"))


class SearchConsoleSyncCommandTests(TestCase):
    def test_sync_persists_daily_query_and_page_metrics(self):
        from datetime import datetime, timedelta
        from unittest.mock import patch
        from zoneinfo import ZoneInfo

        from django.core.management import call_command
        from django.test import override_settings

        from .models import SearchConsoleConnection, SearchConsoleMetric
        from .search_console import encrypt_refresh_token

        with override_settings(SECRET_KEY="search-console-sync-test-secret"):
            connection = SearchConsoleConnection.objects.create(
                site_url="https://mydigigi.ir/",
                refresh_token_encrypted=encrypt_refresh_token("refresh-token"),
            )

            report_date = (
                datetime.now(ZoneInfo("America/Los_Angeles")).date()
                - timedelta(days=3)
            ).isoformat()

            def fake_query(*, dimensions, **kwargs):
                if dimensions == ["date"]:
                    return [{"keys": [report_date], "clicks": 12, "impressions": 300, "ctr": 0.04, "position": 8.5}]
                if dimensions == ["date", "query"]:
                    return [{"keys": [report_date, "nebula vault"], "clicks": 7, "impressions": 100, "ctr": 0.07, "position": 5.0}]
                if dimensions == ["date", "page"]:
                    return [{"keys": [report_date, "https://mydigigi.ir/"], "clicks": 5, "impressions": 200, "ctr": 0.025, "position": 10.0}]
                self.fail(f"Unexpected Search Console dimensions: {dimensions}")

            with (
                patch("seo.management.commands.sync_search_console.refresh_access_token", return_value="access-token"),
                patch("seo.management.commands.sync_search_console.query_search_analytics", side_effect=fake_query),
            ):
                call_command("sync_search_console", days=28)

            self.assertEqual(
                SearchConsoleMetric.objects.filter(connection=connection).count(),
                3,
            )
            query_metric = SearchConsoleMetric.objects.get(
                connection=connection,
                dimension_type=SearchConsoleMetric.DimensionType.QUERY,
            )
            self.assertEqual(query_metric.dimension_value, "nebula vault")
            self.assertEqual(query_metric.clicks, 7)
            connection.refresh_from_db()
            self.assertIsNotNone(connection.last_synced_at)
            self.assertEqual(connection.last_sync_error, "")


class SearchConsoleManualSyncViewTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_superuser(
            username="seo-sync-admin",
            email="seo-sync-admin@example.invalid",
            password="test-password",
        )
        self.client.force_login(
            self.staff,
            backend="django.contrib.auth.backends.ModelBackend",
        )

    def test_post_runs_existing_sync_command_for_28_days(self):
        from unittest.mock import patch

        from django.contrib.messages import get_messages
        from .models import SearchConsoleConnection

        SearchConsoleConnection.objects.create(
            site_url="sc-domain:mydigigi.ir",
            refresh_token_encrypted="encrypted-token",
        )
        with patch("seo.search_console_sync_views.call_command") as run_sync:
            response = self.client.post("/admin/seo-center/search-console/sync/")

        self.assertRedirects(response, "/admin/seo-center/")
        run_sync.assert_called_once()
        self.assertEqual(run_sync.call_args.args, ("sync_search_console",))
        self.assertEqual(run_sync.call_args.kwargs["days"], 28)
        self.assertTrue(any("completed successfully" in str(message) for message in get_messages(response.wsgi_request)))

    def test_sync_requires_post(self):
        response = self.client.get("/admin/seo-center/search-console/sync/")
        self.assertEqual(response.status_code, 405)

    def test_sync_without_active_connection_does_not_run_command(self):
        from unittest.mock import patch

        from django.contrib.messages import get_messages

        with patch("seo.search_console_sync_views.call_command") as run_sync:
            response = self.client.post("/admin/seo-center/search-console/sync/")

        self.assertRedirects(response, "/admin/seo-center/")
        run_sync.assert_not_called()
        self.assertTrue(any("No active Google Search Console property" in str(message) for message in get_messages(response.wsgi_request)))

    def test_sync_requires_staff_access(self):
        self.client.logout()
        customer = get_user_model().objects.create_user(
            username="not-staff",
            email="customer@example.invalid",
            password="test-password",
        )
        self.client.force_login(customer)
        response = self.client.post("/admin/seo-center/search-console/sync/")
        self.assertIn(response.status_code, (302, 403))
