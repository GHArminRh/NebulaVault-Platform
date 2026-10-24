"""Allow-list sanitizer for rich HTML stored by the catalog editor."""

import nh3

ALLOWED_TAGS = {
    "a", "b", "blockquote", "br", "caption", "code", "dd", "del", "div", "dl",
    "dt", "em", "figcaption", "figure", "h1", "h2", "h3", "h4", "h5", "h6",
    "hr", "i", "img", "ins", "li", "mark", "ol", "p", "pre", "s", "small",
    "span", "strong", "sub", "sup", "table", "tbody", "td", "tfoot", "th",
    "thead", "tr", "u", "ul",
}
DROP_CONTENT_TAGS = {
    "button", "embed", "form", "iframe", "input", "link", "math", "meta",
    "object", "script", "style", "svg", "template", "textarea", "video", "audio",
}
ALLOWED_ATTRIBUTES = {
    "*": {"dir", "style", "title"},
    "a": {"href", "target", "rel"},
    "img": {"src", "alt", "width", "height", "loading"},
    "ol": {"start", "reversed", "type"},
    "ul": {"type"},
    "li": {"value"},
    "table": {"border"},
    "td": {"colspan", "rowspan", "align"},
    "th": {"colspan", "rowspan", "align", "scope"},
}
SAFE_STYLE_PROPERTIES = {
    "background-color", "border", "border-collapse", "border-color",
    "border-style", "border-width", "color", "font-family", "font-size",
    "font-style", "font-weight", "height", "line-height", "margin",
    "margin-bottom", "margin-left", "margin-right", "margin-top", "max-width",
    "padding", "padding-bottom", "padding-left", "padding-right", "padding-top",
    "text-align", "text-decoration", "vertical-align", "white-space", "width",
}

_CLEANER = nh3.Cleaner(
    tags=ALLOWED_TAGS,
    clean_content_tags=DROP_CONTENT_TAGS,
    attributes=ALLOWED_ATTRIBUTES,
    link_rel="noopener noreferrer",
    url_schemes={"http", "https", "mailto", "tel"},
    filter_style_properties=SAFE_STYLE_PROPERTIES,
)


def clean_rich_text(value: object) -> str:
    """Return a sanitized HTML fragment suitable for rendering in a page."""
    if value is None:
        return ""
    return _CLEANER.clean(str(value))
