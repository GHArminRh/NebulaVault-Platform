"""Fail-closed configuration for Wagtail media storage."""
from django.core.exceptions import ImproperlyConfigured


def build_default_media_storage_config(
    *,
    backend,
    bucket_name="",
    access_key="",
    secret_key="",
    region_name=None,
    endpoint_url=None,
    custom_domain=None,
    querystring_auth=False,
):
    """Reject incomplete object-storage config instead of silently losing media."""
    backend = (backend or "").strip().lower()
    if backend == "local":
        return {"BACKEND": "django.core.files.storage.FileSystemStorage"}
    if backend != "s3":
        raise ImproperlyConfigured(
            "MEDIA_STORAGE_BACKEND must be either 'local' or 's3'."
        )

    required = {
        "AWS_STORAGE_BUCKET_NAME": bucket_name,
        "AWS_ACCESS_KEY_ID": access_key,
        "AWS_SECRET_ACCESS_KEY": secret_key,
        "AWS_S3_REGION_NAME": region_name,
        "AWS_S3_ENDPOINT_URL": endpoint_url,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ImproperlyConfigured(
            "MEDIA_STORAGE_BACKEND=s3 requires: " + ", ".join(missing)
        )

    return {
        "BACKEND": "sitecms.storage.PrivateMediaS3Storage",
        "OPTIONS": {
            "bucket_name": bucket_name,
            "access_key": access_key,
            "secret_key": secret_key,
            "region_name": region_name,
            "endpoint_url": endpoint_url,
            "custom_domain": custom_domain,
            "file_overwrite": False,
            "default_acl": None,
            "querystring_auth": querystring_auth,
        },
    }
