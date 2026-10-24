"""Admin forms using django-tinymce for staff-managed rich content."""

from django import forms
from tinymce.widgets import TinyMCE

from .models import Product, Release


EDITOR_CONFIG = {
    "height": 420,
    "menubar": "file edit view insert format tools table help",
    "plugins": (
        "advlist autolink lists link image charmap preview anchor "
        "searchreplace visualblocks code fullscreen insertdatetime media "
        "table wordcount"
    ),
    "toolbar": (
        "undo redo | blocks | fontfamily fontsize | "
        "bold italic underline strikethrough | "
        "alignleft aligncenter alignright alignjustify | "
        "bullist numlist outdent indent | "
        "forecolor backcolor | link image media table | "
        "removeformat | searchreplace | code fullscreen"
    ),
    "branding": False,
    "promotion": False,
    "resize": True,
    "statusbar": True,
    "convert_urls": False,
    "relative_urls": False,
    "browser_spellcheck": True,
}


class ProductAdminForm(forms.ModelForm):
    description = forms.CharField(
        required=False,
        widget=TinyMCE(
            attrs={"cols": 80, "rows": 24},
            mce_attrs=EDITOR_CONFIG,
        ),
    )

    class Meta:
        model = Product
        fields = "__all__"


class ReleaseAdminForm(forms.ModelForm):
    release_notes = forms.CharField(
        required=False,
        widget=TinyMCE(
            attrs={"cols": 80, "rows": 24},
            mce_attrs=EDITOR_CONFIG,
        ),
    )

    class Meta:
        model = Release
        fields = "__all__"
