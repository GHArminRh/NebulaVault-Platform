"""Admin forms using the project's centralized django-tinymce configuration."""

from django import forms
from django.conf import settings
from django.urls import reverse_lazy
from tinymce.widgets import TinyMCE

from .models import Product, Release


EDITOR_CONFIG = settings.TINYMCE_DEFAULT_CONFIG


def _staff_editor():
    """Build a fresh widget config and use Django's URL resolver for uploads."""
    return StaffTinyMCE(
        attrs={
            "cols": 80,
            "rows": 24,
            "data-upload-url": reverse_lazy("editor-image-upload"),
        },
        mce_attrs=dict(EDITOR_CONFIG),
    )


class StaffTinyMCE(TinyMCE):
    """TinyMCE widget with a silver UI and a staff-only image upload adapter."""

    class Media:
        css = {
            "all": ("portal/css/tinymce-silver.css",),
        }
        js = (
            "tinymce/tinymce.min.js",
            "portal/js/tinymce_upload.js",
            "tinymce/init_tinymce.js",
        )


class ProductAdminForm(forms.ModelForm):
    description = forms.CharField(required=False, widget=_staff_editor())

    class Meta:
        model = Product
        fields = "__all__"


class ReleaseAdminForm(forms.ModelForm):
    release_notes = forms.CharField(required=False, widget=_staff_editor())

    class Meta:
        model = Release
        fields = "__all__"
