"""Custom Django admin site for Nebula Vault."""

from django.contrib.admin import AdminSite


class NebulaAdminSite(AdminSite):
    """Keep Wagtail-managed libraries out of the legacy Django admin index."""

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        hidden_labels = {"wagtaildocs", "wagtailimages", "taggit"}
        return [app for app in app_list if app.get("app_label") not in hidden_labels]
