"""Template context for staff-only TinyMCE Cloud configuration."""

from django.conf import settings


def tinymce_admin_config(request):
    """Expose the Cloud key only to authenticated staff pages in Django admin."""
    user = getattr(request, "user", None)
    if (
        request.path.startswith("/admin/")
        and user is not None
        and user.is_authenticated
        and user.is_staff
    ):
        return {"tinymce_api_key": settings.TINYMCE_API_KEY}
    return {}
