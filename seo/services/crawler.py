"""Bounded, same-origin crawler for factual technical SEO checks."""

from __future__ import annotations

import ipaddress
import re
import socket
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET
from collections import defaultdict
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.conf import settings


DEFAULT_USER_AGENT = "NebulaSEOBot/1.0 (+site audit; respects robots.txt)"
SKIPPED_SUFFIXES = (".pdf", ".zip", ".exe", ".msi", ".dmg", ".pkg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".css", ".js", ".woff", ".woff2", ".ico")
SKIPPED_PREFIXES = (
    "/admin",
    "/cms",
    "/api",
    "/accounts",
    "/account",
    "/cart",
    "/billing",
    "/checkout",
    "/orders",
    "/dashboard",
    "/subscriptions",
    "/trial",
    "/internal",
    "/search",
    "/media",
    "/static",
)
class CrawlError(Exception):
    """Raised when the configured origin cannot be crawled safely."""


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts = []
        self.description = ""
        self.canonical = ""
        self.robots = ""
        self.h1_count = 0
        self.images_without_alt = 0
        self.links = []
        self._in_title = False
        self._in_h1 = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        tag = tag.lower()
        if tag == "title":
            self._in_title = True
        elif tag == "h1":
            self.h1_count += 1
            self._in_h1 = True
        elif tag == "meta":
            name = (attrs.get("name") or "").strip().lower()
            if name == "description":
                self.description = (attrs.get("content") or "").strip()
            elif name == "robots":
                self.robots = (attrs.get("content") or "").strip().lower()
        elif tag == "link":
            rel = {part.lower() for part in (attrs.get("rel") or "").split()}
            if "canonical" in rel:
                self.canonical = (attrs.get("href") or "").strip()
        elif tag == "img":
            if "alt" not in attrs:
                self.images_without_alt += 1
        elif tag == "a":
            href = (attrs.get("href") or "").strip()
            if href:
                self.links.append(href)

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self._in_title = False
        elif tag.lower() == "h1":
            self._in_h1 = False

    def handle_data(self, data):
        if self._in_title:
            self.title_parts.append(data)

    @property
    def title(self):
        return " ".join(" ".join(self.title_parts).split())


class SameOriginRedirectHandler(HTTPRedirectHandler):
    def __init__(self, crawler):
        super().__init__()
        self.crawler = crawler

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        normalized = self.crawler.normalize_url(newurl)
        if not normalized:
            raise HTTPError(req.full_url, 403, "Cross-origin redirect blocked", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, normalized)


class SiteCrawler:
    """Crawl one configured public origin with strict bounds and safe redirects.

    A custom fetcher can be injected in tests. Production requests use urllib,
    validate public DNS results, restrict redirects to the configured origin,
    and cap response sizes.
    """

    def __init__(
        self,
        base_url=None,
        *,
        max_pages=150,
        timeout=8,
        max_response_bytes=2_000_000,
        request_delay=0.2,
        max_duration_seconds=180,
        fetcher=None,
    ):
        self.base_url = (base_url or settings.SITE_BASE_URL).rstrip("/")
        self.max_pages = max(1, min(int(max_pages), 500))
        self.timeout = max(1, min(int(timeout), 20))
        self.max_response_bytes = max(64_000, min(int(max_response_bytes), 5_000_000))
        self.request_delay = max(0, min(float(request_delay), 2))
        self.max_duration_seconds = max(15, min(int(max_duration_seconds), 600))
        self.fetcher = fetcher
        parsed = urlsplit(self.base_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise CrawlError("SITE_BASE_URL must be a plain absolute HTTP(S) origin.")
        self.origin = (parsed.scheme.lower(), parsed.hostname.lower(), parsed.port or self._default_port(parsed.scheme))
        self.origin_root = urlunsplit((parsed.scheme, parsed.netloc, "/", "", ""))
        self._last_request_at = 0
        self._last_response_metadata = {}
        self._issues = []
        self._issue_keys = set()
        self._robots_rules = []
        self._seen_titles = defaultdict(list)
        self._visited = set()

    @staticmethod
    def _default_port(scheme):
        return 443 if scheme.lower() == "https" else 80

    def normalize_url(self, raw_url, current_url=None):
        if not raw_url:
            return None
        absolute = urljoin(current_url or self.origin_root, raw_url.strip())
        parts = urlsplit(absolute)
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
            return None
        if parts.username or parts.password:
            return None
        port = parts.port or self._default_port(parts.scheme)
        if (parts.scheme.lower(), parts.hostname.lower(), port) != self.origin:
            return None
        path = parts.path or "/"
        if not path.startswith("/"):
            return None
        if any(path == prefix or path.startswith(prefix + "/") for prefix in SKIPPED_PREFIXES):
            return None
        if path.lower().endswith(SKIPPED_SUFFIXES):
            return None
        # Query-string variants are intentionally excluded to avoid crawl traps.
        if parts.query:
            return None
        clean_path = re.sub(r"/{2,}", "/", path)
        if clean_path != "/" and not clean_path.endswith("/") and "." not in clean_path.rsplit("/", 1)[-1]:
            clean_path += "/"
        return urlunsplit((self.origin[0], parts.netloc, clean_path, "", ""))

    def _validate_public_host(self):
        host = self.origin[1]
        try:
            addresses = {item[4][0] for item in socket.getaddrinfo(host, self.origin[2], type=socket.SOCK_STREAM)}
        except OSError as exc:
            raise CrawlError(f"Could not resolve configured public host: {exc}") from exc
        if not addresses:
            raise CrawlError("Configured public host did not resolve to an IP address.")
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if not ip.is_global:
                raise CrawlError("Crawler refused a host that resolves to a non-public IP address.")

    @staticmethod
    def _safe_response_headers(headers):
        """Keep only non-sensitive headers useful for diagnosing proxy responses."""
        names = (
            "Server",
            "CF-Ray",
            "CF-Mitigated",
            "CF-Cache-Status",
            "Retry-After",
            "Content-Type",
            "Via",
            "X-Request-ID",
        )
        return {
            name.lower(): str(headers.get(name, ""))[:200]
            for name in names
            if headers.get(name)
        }

    @staticmethod
    def _retry_delay(status, headers):
        """Return a safe retry delay, or None when Retry-After is too long."""
        retry_after = headers.get("Retry-After") if headers else None
        if retry_after:
            try:
                delay = max(0.0, float(retry_after))
            except (TypeError, ValueError):
                try:
                    retry_at = parsedate_to_datetime(str(retry_after))
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=timezone.utc)
                    delay = max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
                except (TypeError, ValueError, OverflowError):
                    delay = 1.0
            # Do not keep a web request open for a long server-imposed cooldown.
            # Record the response and let the operator decide when to retry.
            return delay if delay <= 2.0 else None
        return 1.0 if status == 429 else 0.25

    def _http_diagnostics(self, status, final_url):
        parts = [f"HTTP {status}", f"Final URL: {final_url}"]
        parts.extend(
            f"{name}: {value}"
            for name, value in self._last_response_metadata.items()
        )
        return "; ".join(parts)

    def _fetch(self, url, accept="text/html,application/xhtml+xml"):
        """Fetch with one bounded retry and retain safe response diagnostics."""
        if not self.fetcher:
            self._validate_public_host()

        self._last_response_metadata = {}
        retryable_statuses = {429, 500, 502, 503, 504, 520, 521, 522, 523, 524}
        for attempt in range(2):
            elapsed = time.monotonic() - self._last_request_at
            if elapsed < self.request_delay:
                time.sleep(self.request_delay - elapsed)
            try:
                if self.fetcher:
                    result = self.fetcher(url, accept=accept)
                    headers = result[4] if len(result) > 4 and isinstance(result[4], dict) else {}
                    status = result[0]
                    self._last_response_metadata = self._safe_response_headers(headers)
                    self._last_request_at = time.monotonic()
                    if status in retryable_statuses and attempt == 0:
                        delay = self._retry_delay(status, headers)
                        if delay is not None:
                            time.sleep(delay)
                            continue
                    return result[:4]

                request = Request(
                    url,
                    headers={
                        "User-Agent": DEFAULT_USER_AGENT,
                        "Accept": accept,
                        "Accept-Encoding": "identity",
                    },
                )
                opener = build_opener(SameOriginRedirectHandler(self))
                try:
                    response = opener.open(request, timeout=self.timeout)
                except HTTPError as exc:
                    headers = exc.headers or {}
                    self._last_response_metadata = self._safe_response_headers(headers)
                    self._last_request_at = time.monotonic()
                    if exc.code in retryable_statuses and attempt == 0:
                        delay = self._retry_delay(exc.code, headers)
                        if delay is not None:
                            exc.close()
                            time.sleep(delay)
                            continue
                    return exc.code, headers.get("Content-Type", ""), b"", exc.geturl()

                with response:
                    self._last_response_metadata = self._safe_response_headers(response.headers)
                    content_type = response.headers.get("Content-Type", "").lower()
                    body = response.read(self.max_response_bytes + 1)
                    if len(body) > self.max_response_bytes:
                        raise CrawlError("Response exceeded the configured size limit.")
                    self._last_request_at = time.monotonic()
                    return response.status, content_type, body, response.geturl()
            except (URLError, OSError, TimeoutError) as exc:
                self._last_request_at = time.monotonic()
                if attempt == 0:
                    time.sleep(0.25)
                    continue
                raise CrawlError(str(exc)) from exc

        raise CrawlError("The request failed after a transient retry.")

    def _add_issue(self, url, code, severity, title, details="", recommendation=""):
        key = (url, code)
        if key in self._issue_keys:
            return
        self._issue_keys.add(key)
        self._issues.append(
            {
                "url": url,
                "code": code,
                "severity": severity,
                "title": title,
                "details": details[:4000],
                "recommendation": recommendation[:4000],
            }
        )

    def _read_robots(self):
        robots_url = urljoin(self.origin_root, "robots.txt")
        try:
            status, content_type, body, final_url = self._fetch(
                robots_url, accept="text/plain,*/*"
            )
        except CrawlError as exc:
            self._add_issue(
                robots_url,
                "robots-fetch-failed",
                "warning",
                "Could not read robots.txt",
                str(exc),
                "Verify that robots.txt is reachable from the public website.",
            )
            return []
        if status == 404:
            self._add_issue(
                robots_url,
                "robots-not-found",
                "warning",
                "robots.txt was not found",
                "HTTP 404",
                "Serve a valid robots.txt file that states crawler access rules and the sitemap location.",
            )
            return []
        if status >= 400:
            self._add_issue(
                robots_url,
                "robots-http-error",
                "warning",
                "robots.txt returned an HTTP error",
                f"HTTP {status}",
                "Return a valid robots.txt response or intentionally configure the route.",
            )
            return []
        try:
            text = body.decode("utf-8-sig", errors="replace")
        except AttributeError:
            text = str(body)
        active = False
        rules = []
        sitemap_urls = []
        for raw_line in text.splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            key, value = [part.strip() for part in line.split(":", 1)]
            key = key.lower()
            if key == "user-agent":
                active = value == "*" or value.lower() in {"nebulaseobot", "nebulaseobot/1.0"}
            elif active and key in {"allow", "disallow"} and value:
                rules.append((key == "allow", value))
            elif key == "sitemap" and value:
                normalized = self.normalize_url(value)
                if normalized:
                    sitemap_urls.append(normalized)
        self._robots_rules = rules
        return sitemap_urls

    def _allowed_by_robots(self, url):
        path = urlsplit(url).path
        matching = [
            (len(pattern.rstrip("*")), allowed)
            for allowed, pattern in self._robots_rules
            if path.startswith(pattern.rstrip("*"))
        ]
        if not matching:
            return True
        # The most specific rule wins; Allow wins a tie, as specified by robots.txt.
        specificity = max(length for length, _ in matching)
        return any(allowed for length, allowed in matching if length == specificity)

    def _sitemap_urls(self, candidates):
        urls = []
        queue = list(candidates) + [urljoin(self.origin_root, "sitemap.xml")]
        seen_sitemaps = set()
        while queue and len(urls) < self.max_pages:
            sitemap_url = self.normalize_url(queue.pop(0))
            if not sitemap_url or sitemap_url in seen_sitemaps:
                continue
            seen_sitemaps.add(sitemap_url)
            try:
                status, content_type, body, final_url = self._fetch(
                    sitemap_url, accept="application/xml,text/xml,*/*"
                )
            except CrawlError as exc:
                self._add_issue(
                    sitemap_url,
                    "sitemap-fetch-failed",
                    "warning",
                    "Sitemap could not be fetched",
                    str(exc),
                    "Verify that the sitemap URL is reachable and returns valid XML.",
                )
                continue
            if status >= 400:
                self._add_issue(
                    sitemap_url,
                    "sitemap-http-error",
                    "warning",
                    f"Sitemap returned HTTP {status}",
                    f"HTTP {status}",
                    "Fix the sitemap endpoint or remove the unavailable sitemap from the sitemap index.",
                )
                continue
            if not body:
                self._add_issue(
                    sitemap_url,
                    "empty-sitemap",
                    "warning",
                    "Sitemap response is empty",
                    "The endpoint returned an empty response body.",
                    "Return a valid XML sitemap containing the site's indexable URLs.",
                )
                continue
            try:
                root = ET.fromstring(body)
            except ET.ParseError:
                self._add_issue(
                    sitemap_url,
                    "invalid-sitemap-xml",
                    "warning",
                    "Sitemap XML could not be parsed",
                    "The sitemap response is not valid XML.",
                    "Validate the sitemap XML and its content type.",
                )
                continue
            root_name = root.tag.rsplit("}", 1)[-1].lower()
            locs = [
                (node.text or "").strip()
                for node in root.iter()
                if node.tag.rsplit("}", 1)[-1].lower() == "loc"
            ]
            for loc in locs:
                normalized = self.normalize_url(loc)
                if not normalized:
                    continue
                if root_name == "sitemapindex":
                    if normalized not in seen_sitemaps:
                        queue.append(normalized)
                elif normalized not in urls:
                    urls.append(normalized)
                    if len(urls) >= self.max_pages:
                        break
        return urls

    def _inspect_page(self, url, status, content_type, body, final_url):
        if status >= 400:
            self._add_issue(
                url,
                "http-error",
                "error" if status >= 500 else "warning",
                f"Page returned HTTP {status}",
                f"Final URL: {final_url}",
                "Fix the response or update internal links that point to this URL.",
            )
            return []
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            return []
        parser = PageParser()
        try:
            parser.feed(body.decode("utf-8", errors="replace"))
            parser.close()
        except Exception as exc:
            self._add_issue(
                url,
                "html-parse-error",
                "warning",
                "Page HTML could not be fully parsed",
                str(exc),
                "Validate the page's HTML response.",
            )
            return []

        effective_url = self.normalize_url(final_url) or url
        if effective_url != url:
            self._add_issue(
                url,
                "redirected-url",
                "info",
                "Page redirects to another URL",
                f"Final URL: {effective_url}",
                "Update internal links and sitemap entries to point directly to the final URL where practical.",
            )

        title = parser.title
        if not title:
            self._add_issue(url, "missing-title", "error", "Page has no title element", recommendation="Add a unique, descriptive HTML title.")
        elif len(title) > 60:
            self._add_issue(url, "long-title", "warning", "Page title is longer than 60 characters", f"Current title length: {len(title)}", "Consider making the title more concise without sacrificing clarity.")
        self._seen_titles[title.casefold()].append(url)

        if not parser.description:
            self._add_issue(url, "missing-meta-description", "warning", "Page has no meta description", recommendation="Write a unique summary that accurately describes the page.")
        elif len(parser.description) > 160:
            self._add_issue(url, "long-meta-description", "info", "Meta description is longer than 160 characters", f"Current description length: {len(parser.description)}", "Consider shortening the description while preserving its main value proposition.")

        if parser.h1_count == 0:
            self._add_issue(url, "missing-h1", "warning", "Page has no H1 heading", recommendation="Add one clear primary heading that describes the page.")
        elif parser.h1_count > 1:
            self._add_issue(url, "multiple-h1", "info", "Page has multiple H1 headings", f"H1 count: {parser.h1_count}", "Review the heading hierarchy and ensure the primary page topic is clear.")

        if not parser.canonical:
            self._add_issue(url, "missing-canonical", "warning", "Page has no canonical link", recommendation="Add a canonical URL when the page should have a preferred indexable URL.")
        else:
            canonical_url = urljoin(url, parser.canonical)
            canonical_parts = urlsplit(canonical_url)
            if (canonical_parts.scheme.lower(), (canonical_parts.hostname or "").lower(), canonical_parts.port or self._default_port(canonical_parts.scheme)) != self.origin:
                self._add_issue(url, "external-canonical", "error", "Canonical URL points outside the site", canonical_url, "Use a canonical URL on the intended public site origin.")
            elif self.normalize_url(canonical_url) != effective_url:
                self._add_issue(url, "canonical-mismatch", "warning", "Canonical URL differs from the crawled URL", canonical_url, "Confirm that the canonical target is intentional and indexable.")

        if "noindex" in parser.robots:
            self._add_issue(url, "noindex-page", "info", "Page is marked noindex", parser.robots, "Confirm that excluding this public page from search results is intentional.")

        if parser.images_without_alt:
            self._add_issue(url, "images-missing-alt", "warning", "Images are missing alternative text", f"Images without useful alt attributes: {parser.images_without_alt}", "Add concise, meaningful alt text to informative images; use empty alt text for decorative images.")

        discovered = []
        for href in parser.links:
            target = self.normalize_url(href, current_url=effective_url)
            if target and self._allowed_by_robots(target) and target not in self._visited:
                discovered.append(target)
        return discovered

    def crawl(self):
        self._validate_public_host() if not self.fetcher else None
        sitemap_candidates = self._read_robots()
        sitemap_urls = self._sitemap_urls(sitemap_candidates)
        start_urls = [self.normalize_url(self.origin_root)] + sitemap_urls
        queue = [url for url in start_urls if url and self._allowed_by_robots(url)]
        pages_scanned = 0
        started_at = time.monotonic()

        while queue and pages_scanned < self.max_pages:
            if time.monotonic() - started_at >= self.max_duration_seconds:
                self._add_issue(
                    self.origin_root,
                    "crawl-time-limit",
                    "warning",
                    "Crawler reached its time limit",
                    f"Stopped after {self.max_duration_seconds} seconds.",
                    "Run a larger audit window or reduce per-request latency before increasing crawl limits.",
                )
                break
            url = queue.pop(0)
            if url in self._visited or not self._allowed_by_robots(url):
                continue
            self._visited.add(url)
            try:
                status, content_type, body, final_url = self._fetch(url)
            except CrawlError as exc:
                self._add_issue(
                    url,
                    "fetch-failed",
                    "error",
                    "Page could not be fetched",
                    str(exc),
                    "Check server availability, TLS, and the page response.",
                )
                pages_scanned += 1
                continue
            pages_scanned += 1
            discovered = self._inspect_page(url, status, content_type, body, final_url)
            for target in discovered:
                if target not in self._visited and target not in queue and len(queue) < self.max_pages * 3:
                    queue.append(target)

        for title, page_urls in self._seen_titles.items():
            if title and len(page_urls) > 1:
                for page_url in page_urls:
                    self._add_issue(
                        page_url,
                        "duplicate-title",
                        "warning",
                        "Page title is duplicated",
                        f"Shared with: {', '.join(page for page in page_urls if page != page_url)[:1500]}",
                        "Give each important indexable page a distinct title.",
                    )

        return {
            "pages_scanned": pages_scanned,
            "issues": self._issues,
        }
