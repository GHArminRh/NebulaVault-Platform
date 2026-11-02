"""Native, accessible image uploader widget for Nebula Vault's Django admin."""

from pathlib import Path

from django import forms
from django.conf import settings


MAX_IMAGE_UPLOAD_BYTES = 12 * 1024 * 1024


class NebulaImageUploaderWidget(forms.ClearableFileInput):
    """Image input with drag/drop, preview and real multipart upload progress."""

    template_name = "admin/widgets/nebula_image_uploader.html"

    class Media:
        css = {"all": ("portal/css/nebula-image-uploader.css",)}
        js = ("portal/js/nebula-image-uploader.js",)

    def __init__(self, attrs=None):
        attributes = dict(attrs or {})
        attributes.setdefault("accept", "image/*")
        attributes["data-nv-image-input"] = "true"
        attributes["class"] = (
            f"{attributes.get('class', '')} nv-image-uploader__input".strip()
        )
        super().__init__(attributes)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        widget = context["widget"]
        widget["max_upload_bytes"] = MAX_IMAGE_UPLOAD_BYTES
        widget["initial_url"] = ""
        widget["initial_name"] = ""

        if value and getattr(value, "name", ""):
            widget["initial_name"] = Path(value.name).name
            try:
                widget["initial_url"] = value.url
            except (AttributeError, ValueError):
                widget["initial_url"] = ""

        return context
