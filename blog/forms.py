from django import forms
from tinymce.widgets import TinyMCE

from .models import BlogPost


class BlogPostAdminForm(forms.ModelForm):
    content = forms.CharField(widget=TinyMCE(attrs={"cols": 100, "rows": 32}))

    class Meta:
        model = BlogPost
        fields = "__all__"
