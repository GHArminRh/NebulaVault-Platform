"""Route the public root URL to the published django CMS homepage safely."""

from django.http import Http404

from cms.views import details as cms_page_details

from .views import home as storefront_home


def cms_home(request):
    """Render the CMS homepage; keep the established storefront as a safe fallback."""
    try:
        response = cms_page_details(request, slug="")
    except Http404:
        return storefront_home(request)

    # A missing/unpublished CMS root must not take the public storefront down.
    if response.status_code == 404:
        return storefront_home(request)
    return response
