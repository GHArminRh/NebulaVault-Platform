"""Django widget for Nebula Vault's TinyMCE-based rich-text editor.

This module replaces the django-tinymce integration package. The editor's
configuration and upload integration are maintained by Nebula Vault itself.
"""
import json

from django import forms
from django.utils.html import json_script


class NebulaTinyMCE(forms.Textarea):
    """Textarea enhanced by the Nebula Vault TinyMCE initializer."""

    def __init__(self, attrs=None, config=None):
        self.config = dict(config or {})
        super().__init__(attrs=attrs)

    class Media:
        # The Django integration is local. TinyMCE's upstream browser runtime is
        # pinned to a fixed release rather than being loaded from an unversioned URL.
        js = (
            "https://cdn.jsdelivr.net/npm/tinymce@7.8.0/tinymce.min.js",
            "portal/js/tinymce_upload.js",
            "portal/js/init_tinymce.js",
        )

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["attrs"]["data-tinymce-config"] = json.dumps(
            self.config, ensure_ascii=False, separators=(",", ":")
        )
        return context
