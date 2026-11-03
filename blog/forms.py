from django import forms
from django.core.exceptions import ValidationError
from tinymce.widgets import TinyMCE

from portal.widgets import MAX_IMAGE_UPLOAD_BYTES, NebulaImageUploaderWidget

from .models import BlogPost
from .widgets import BlogTagMultiSelectWidget


class BlogPostAdminForm(forms.ModelForm):
    content = forms.CharField(widget=TinyMCE(attrs={"cols": 100, "rows": 32}))
    img = forms.ImageField(required=False, widget=NebulaImageUploaderWidget())

    class Meta:
        model = BlogPost
        fields = "__all__"
        widgets = {"tags": BlogTagMultiSelectWidget}

    def clean_img(self):
        image = self.cleaned_data.get("img")
        if image and image.size > MAX_IMAGE_UPLOAD_BYTES:
            max_mb = MAX_IMAGE_UPLOAD_BYTES // (1024 * 1024)
            raise ValidationError(
                f"Image is too large. The maximum allowed size is {max_mb} MB."
            )
        return image
