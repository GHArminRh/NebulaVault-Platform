"""S3-compatible storage that serves public Wagtail images through Django.

The B2 bucket can remain private: the application uses its credentials to read
objects and exposes only stable, HMAC-authenticated proxy URLs to the browser.
Wagtail documents use WAGTAILDOCS_SERVE_METHOD="serve_view" so collection
privacy checks happen before Django streams a document.
"""
from urllib.parse import urlencode

from django.urls import reverse
from storages.backends.s3 import S3Storage

from .media_proxy import media_proxy_signature


class PrivateMediaS3Storage(S3Storage):
    """Store files in S3/B2 but never return a provider URL to the browser."""

    def url(self, name, parameters=None, expire=None, http_method=None):
        # Public CMS images use a stable signed application URL. Do not forward
        # S3 query parameters or credentials to the client.
        path = reverse("private-media-proxy", kwargs={"path": name})
        query = urlencode({"signature": media_proxy_signature(name)})
        return f"{path}?{query}"
