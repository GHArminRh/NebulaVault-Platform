"""Admin forms using Nebula Vault's in-project rich-text editor widget."""

from django import forms
from django.conf import settings
from django.urls import reverse_lazy

from nebula_editor.widgets import NebulaTinyMCE
from .models import Product, Release


EDITOR_CONFIG = settings.NEBULA_EDITOR_CONFIG


def _staff_editor():
    """Create an editor configured for the staff-only image upload endpoint."""
    return NebulaTinyMCE(
        attrs={
            "cols": 80,
            "rows": 24,
            "data-upload-url": reverse_lazy("editor-image-upload"),
        },
        config=dict(EDITOR_CONFIG),
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
