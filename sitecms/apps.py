from django.apps import AppConfig
from wagtail.users.apps import WagtailUsersAppConfig as BaseWagtailUsersAppConfig


class SiteCMSConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sitecms"
    verbose_name = "Nebula Vault CMS"


class WagtailUsersAppConfig(BaseWagtailUsersAppConfig):
    """Keep Wagtail user management compatible with the staff account model."""

    user_viewset = "sitecms.viewsets.UserViewSet"
