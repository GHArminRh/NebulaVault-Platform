"""Custom Django admin site for Nebula Vault."""

from django.contrib.admin import AdminSite
from django.urls import reverse


class NebulaAdminSite(AdminSite):
    """Keep Wagtail-managed libraries out of the legacy Django admin index."""

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        hidden_labels = {"wagtaildocs", "wagtailimages", "taggit"}
        app_list = [app for app in app_list if app.get("app_label") not in hidden_labels]

        # The dashboard has its own protected route rather than a database
        # model, so Django does not add it to the app index automatically.
        # Expose it as a view-only entry alongside the SEO Center models.
        if request.user.has_perm("seo.view_seoauditrun"):
            from seo.models import SEOAuditRun

            for app in app_list:
                if app.get("app_label") == "seo":
                    app["models"].insert(
                        0,
                        {
                            "model": SEOAuditRun,
                            "name": "SEO Center dashboard",
                            "object_name": "SEOCenterDashboard",
                            "perms": {
                                "add": False,
                                "change": False,
                                "delete": False,
                                "view": True,
                            },
                            "admin_url": reverse("seo-dashboard"),
                            "add_url": None,
                            "view_only": True,
                        },
                    )
                    break

        return app_list
