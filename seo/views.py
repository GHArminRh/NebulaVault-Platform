"""Public robots and sitemap endpoints for the complete Django/Wagtail site."""

from xml.etree import ElementTree

from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET

from blog.models import BlogPost
from catalog.models import Product


SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ElementTree.register_namespace("", SITEMAP_NS)


def _xml_response(root):
    body = ElementTree.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
    )
    return HttpResponse(body, content_type="application/xml; charset=utf-8")


def _absolute_url(path):
    return f"{settings.SITE_BASE_URL.rstrip('/')}{path}"


def _urlset(entries):
    root = ElementTree.Element(f"{{{SITEMAP_NS}}}urlset")
    for path, lastmod in entries:
        item = ElementTree.SubElement(root, f"{{{SITEMAP_NS}}}url")
        ElementTree.SubElement(item, f"{{{SITEMAP_NS}}}loc").text = _absolute_url(path)
        if lastmod:
            ElementTree.SubElement(item, f"{{{SITEMAP_NS}}}lastmod").text = lastmod.isoformat()
    response = _xml_response(root)
    response["Cache-Control"] = "public, max-age=300"
    return response


@require_GET
def robots_txt(request):
    """Tell compliant crawlers which utility routes are private and where the sitemap lives."""
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /cms/",
        "Disallow: /api/",
        "Disallow: /accounts/",
        "Disallow: /cart/",
        "Disallow: /billing/",
        "Disallow: /checkout/",
        "Disallow: /orders/",
        "Disallow: /dashboard/",
        "Disallow: /subscriptions/",
        "Disallow: /trial/",
        "Disallow: /search/",
        "",
        f"Sitemap: {_absolute_url('/sitemap.xml')}",
        "",
    ]
    response = HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")
    response["Cache-Control"] = "public, max-age=3600"
    return response


@require_GET
def sitemap_index(request):
    """Index separate sitemaps for Wagtail, products, articles, and key public pages."""
    root = ElementTree.Element(f"{{{SITEMAP_NS}}}sitemapindex")
    for path in (
        "/sitemap-wagtail.xml",
        "/sitemap-pages.xml",
        "/sitemap-products.xml",
        "/sitemap-blog.xml",
    ):
        item = ElementTree.SubElement(root, f"{{{SITEMAP_NS}}}sitemap")
        ElementTree.SubElement(item, f"{{{SITEMAP_NS}}}loc").text = _absolute_url(path)
    response = _xml_response(root)
    response["Cache-Control"] = "public, max-age=300"
    return response


@require_GET
def core_sitemap(request):
    paths = (
        reverse("portal:home"),
        reverse("portal:products"),
        reverse("portal:pricing"),
        reverse("blog:post_list"),
    )
    return _urlset([(path, None) for path in paths])


@require_GET
def product_sitemap(request):
    products = Product.objects.filter(is_active=True).only("slug", "updated_at")
    return _urlset(
        [
            (reverse("portal:product_detail", kwargs={"slug": product.slug}), product.updated_at)
            for product in products
        ]
    )


@require_GET
def blog_sitemap(request):
    posts = BlogPost.objects.filter(
        status=BlogPost.Status.PUBLISHED,
        published_at__lte=timezone.now(),
    ).only("slug", "updated_at")
    return _urlset(
        [
            (reverse("blog:post_detail", kwargs={"slug": post.slug}), post.updated_at)
            for post in posts
        ]
    )
