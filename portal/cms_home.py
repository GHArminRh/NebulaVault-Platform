from django.http import Http404

from cms.views import details as cms_page_details

from .views import home as storefront_home


def cms_home(request):
    """Serve the editable CMS homepage at /, preserving the storefront fallback.

    The existing storefront view remains the safe fallback when no published
    Persian CMS homepage is configured. Other application routes are untouched.
    """
    try:
        response = cms_page_details(request, slug="")
    except Http404:
        return storefront_home(request)

    if response.status_code == 404:
        return storefront_home(request)
    return response
