from django.apps import AppConfig


class CmsSiteSeedConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cms_site_seed"
    verbose_name = "CMS site content initialization"
