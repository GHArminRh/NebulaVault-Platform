"""Application configuration for the project's customized Django admin."""

from django.contrib.admin.apps import AdminConfig


class NebulaAdminConfig(AdminConfig):
    default_site = "config.admin.NebulaAdminSite"
