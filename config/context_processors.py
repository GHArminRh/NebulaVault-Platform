from django.conf import settings


def ckeditor_config(request):
    """Expose the CKEditor license key to the editor bootstrap script."""
    return {"ckeditor_license_key": settings.CKEDITOR_LICENSE_KEY}
