"""Secure Django streaming endpoint for public Wagtail image assets."""
import logging
import mimetypes
import posixpath

from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, HttpResponse
from django.utils.crypto import constant_time_compare, salted_hmac
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


def media_proxy_signature(name):
    """Return a deterministic, non-expiring signature for a public media key."""
    return salted_hmac(
        "sitecms.private_media_proxy.v1",
        str(name),
        secret=settings.SECRET_KEY,
    ).hexdigest()


def _valid_storage_name(name):
    if not name or name.startswith("/") or "\\\\" in name or "\\0" in name:
        return False
    if posixpath.normpath(name) != name:
        return False
    return all(part not in {"", ".", ".."} for part in name.split("/"))


@require_GET
def private_media_proxy(request, path):
    """Stream a signed public image from private object storage via Django."""
    signature = request.GET.get("signature", "")
    if (
        not _valid_storage_name(path)
        or not signature
        or not constant_time_compare(signature, media_proxy_signature(path))
    ):
        raise Http404

    try:
        media_file = default_storage.open(path, "rb")
    except ClientError as exc:
        error_code = str(exc.response.get("Error", {}).get("Code", ""))
        if error_code in {"NoSuchKey", "404", "NotFound"}:
            raise Http404 from exc
        logger.exception("Object storage rejected a media read")
        return HttpResponse("Media storage temporarily unavailable", status=503)
    except FileNotFoundError as exc:
        # A missing local file is a missing resource, not a storage outage.
        raise Http404 from exc
    except (BotoCoreError, OSError, ValueError):
        logger.exception("Unable to stream media from object storage")
        return HttpResponse("Media storage temporarily unavailable", status=503)

    content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    # Only common raster image formats are rendered inline. Other uploads,
    # including SVG/HTML, are forced to download to reduce script-execution risk.
    inline_types = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/avif"}
    response = FileResponse(
        media_file,
        content_type=content_type,
        as_attachment=content_type not in inline_types,
        filename=posixpath.basename(path),
    )
    response["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=3600"
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    response["Cross-Origin-Resource-Policy"] = "same-site"
    return response
