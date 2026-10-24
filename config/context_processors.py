"""Template context for optional third-party frontend integrations."""
from django.conf import settings


def ckeditor_config(request):
    """Expose only the public CKEditor client configuration to templates."""
    return {
        "ckeditor_config": {
            "licenseKey": getattr(settings, "CKEDITOR_LICENSE_KEY", ""),
            "cloudServicesTokenUrl": getattr(settings, "CKEDITOR_CLOUD_SERVICES_TOKEN_URL", ""),
        }
    }
