"""Admin forms using Nebula Vault's in-project rich-text editor widget."""

from django import forms

from tinymce.widgets import TinyMCE
from .models import Product, Release



def _staff_editor():
    """Use the supported django-tinymce widget and shared settings."""
    return TinyMCE(attrs={"cols": 80, "rows": 24})


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
