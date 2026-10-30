"""Route the public root URL to the published django CMS homepage safely."""

from django.http import Http404

from cms.models import PageUrl
from cms.utils import get_current_site
from cms.views import details as cms_page_details

from .views import home as storefront_home


def cms_home(request):
    """Render the published CMS root page, falling back to the storefront if absent."""
    site = get_current_site(request)

    # django CMS renders its welcome page with HTTP 200 when a site has no
    # pages at all. Check for a published root PageUrl first so an empty or
    # partially bootstrapped CMS never replaces the existing storefront.
    language = getattr(request, "LANGUAGE_CODE", None) or "fa"
    has_published_root = PageUrl.objects.filter(
        site=site,
        language=language,
        path__in=("", "/"),
    ).exists()
    if not has_published_root:
        return storefront_home(request)

    try:
        response = cms_page_details(request, slug="")
    except Http404:
        return storefront_home(request)

    # A root page without a usable published version must not take the public
    # storefront down.
    if response.status_code == 404:
        return storefront_home(request)
    return response
