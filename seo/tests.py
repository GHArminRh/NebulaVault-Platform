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


class SEORobotsAndSitemapTests(TestCase):
    def test_robots_txt_blocks_private_routes_and_advertises_sitemap(self):
        from django.test import override_settings

        with override_settings(SITE_BASE_URL="https://mydigigi.ir"):
            response = self.client.get("/robots.txt")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Disallow: /admin/")
        self.assertContains(response, "Disallow: /cart/")
        self.assertContains(response, "Sitemap: https://mydigigi.ir/sitemap.xml")

    def test_sitemap_index_includes_all_site_content_sitemaps(self):
        from django.test import override_settings
        from xml.etree import ElementTree

        with override_settings(SITE_BASE_URL="https://mydigigi.ir"):
            response = self.client.get("/sitemap.xml")

        self.assertEqual(response.status_code, 200)
        root = ElementTree.fromstring(response.content)
        locations = [
            node.text
            for node in root.iter()
            if node.tag.endswith("loc")
        ]
        self.assertIn("https://mydigigi.ir/sitemap-products.xml", locations)
        self.assertIn("https://mydigigi.ir/sitemap-blog.xml", locations)
        self.assertIn("https://mydigigi.ir/sitemap-wagtail.xml", locations)
