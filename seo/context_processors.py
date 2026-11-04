from django.conf import settings


PRIVATE_PATH_PREFIXES = (
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
    "/search",
)


def seo_context(request):
    """Provide a stable canonical origin and keep private utility pages out of indexes."""
    path = request.path or "/"
    is_private = any(
        path == prefix or path.startswith(prefix + "/")
        for prefix in PRIVATE_PATH_PREFIXES
    )
    canonical_url = f"{settings.SITE_BASE_URL.rstrip('/')}{path}"
    return {
        "seo_canonical_url": canonical_url,
        "seo_default_robots": "noindex,nofollow" if is_private else "index,follow",
    }
