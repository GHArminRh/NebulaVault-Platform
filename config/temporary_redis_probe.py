"""Temporary one-shot Redis cache diagnostic endpoint.

Remove this module and its URL after the deployment probe has been run.
"""
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_GET

from django_redis import get_redis_connection


@require_GET
def temporary_redis_cache_probe(request):
    # High-entropy temporary URL; this endpoint must be removed immediately
    # after the diagnostic has been collected.
    if request.path != "/__ops/cache-probe-9f4b7c2e81d6a305f0c9b7e2a64d18f3c8a1e5b907d2f6a4c1e8b3d5f7092a6c/":
        raise Http404

    result = {
        "cache_backend": settings.CACHES["default"]["BACKEND"],
        "redis_url_configured": bool(getattr(settings, "REDIS_URL", "")),
        "redis_ping": False,
        "cache_set": False,
        "cache_get_matches": False,
    }
    key = f"__nebula_cache_probe__:{uuid4().hex}"

    try:
        client = get_redis_connection("default")
        result["redis_ping"] = bool(client.ping())
    except Exception as exc:
        result["redis_error"] = type(exc).__name__

    try:
        result["cache_set"] = bool(cache.set(key, "nebula-cache-ok", timeout=90))
        result["cache_get_matches"] = cache.get(key) == "nebula-cache-ok"
    except Exception as exc:
        result["cache_error"] = type(exc).__name__
    finally:
        try:
            cache.delete(key)
        except Exception:
            pass

    result["overall_ok"] = (
        result["redis_url_configured"]
        and result["redis_ping"]
        and result["cache_set"]
        and result["cache_get_matches"]
    )
    response = JsonResponse(result)
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response
