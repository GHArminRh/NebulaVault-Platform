"""Template filter for rendering sanitized catalog rich text."""

from django import template
from django.utils.safestring import mark_safe

from catalog.rich_text import clean_rich_text

register = template.Library()


@register.filter
def rich_text(value):
    """Sanitize allowed rich HTML, then mark only the sanitized fragment safe."""
    if value is None or value == "":
        return ""
    return mark_safe(clean_rich_text(value))
