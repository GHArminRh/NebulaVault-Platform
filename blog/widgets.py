from django import forms


class BlogTagMultiSelectWidget(forms.SelectMultiple):
    """Searchable, accessible multi-select for blog tags in Django admin."""

    template_name = "admin/widgets/blog_tag_multi_select.html"

    class Media:
        css = {"all": ("portal/css/admin-blog-tag-multiselect.css",)}
        js = ("portal/js/admin-blog-tag-multiselect.js",)}
