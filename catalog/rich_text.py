"""Allow-list sanitizer for rich HTML stored by the catalog editor."""

import re
from urllib.parse import urlsplit

import nh3


ALLOWED_TAGS = {
    "a", "b", "blockquote", "br", "caption", "code", "dd", "del", "div", "dl",
    "dt", "em", "figcaption", "figure", "h1", "h2", "h3", "h4", "h5", "h6",
    "hr", "i", "iframe", "img", "ins", "li", "mark", "ol", "p", "pre", "s",
    "small", "span", "strike", "strong", "sub", "sup", "table", "tbody", "td",
    "tfoot", "th", "thead", "tr", "u", "ul",
}
DROP_CONTENT_TAGS = {
    "button", "embed", "form", "input", "link", "math", "meta", "object",
    "script", "style", "svg", "template", "textarea", "video", "audio",
}
ALLOWED_ATTRIBUTES = {
    "*": {"dir", "style", "title"},
    "a": {"href", "target", "rel"},
    "img": {"src", "alt", "width", "height", "loading"},
    "iframe": {"src", "width", "height", "allowfullscreen"},
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
    "page-break-after", "text-align", "text-decoration", "vertical-align",
    "white-space", "width",
}
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "www.youtube-nocookie.com"}


def _allowed_embed_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or parsed.username or parsed.password:
            return False
        if parsed.port not in (None, 443):
            return False
        host = (parsed.hostname or "").lower()
        if host in YOUTUBE_HOSTS:
            return bool(re.fullmatch(r"/embed/[A-Za-z0-9_-]{6,20}/?", parsed.path))
        if host == "player.vimeo.com":
            return bool(re.fullmatch(r"/video/[0-9]{5,12}/?", parsed.path))
    except (TypeError, ValueError):
        return False
    return False


def _filter_attribute(tag: str, attribute: str, value: str) -> str | None:
    if tag == "iframe" and attribute == "src" and not _allowed_embed_url(value):
        return None
    if tag == "a" and attribute == "target" and value not in {"_blank", "_self"}:
        return None
    if tag in {"img", "iframe"} and attribute in {"width", "height"}:
        try:
            dimension = int(value)
        except (TypeError, ValueError):
            return None
        if dimension < 1 or dimension > 4000:
            return None
    return value


_CLEANER = nh3.Cleaner(
    tags=ALLOWED_TAGS,
    clean_content_tags=DROP_CONTENT_TAGS,
    attributes=ALLOWED_ATTRIBUTES,
    attribute_filter=_filter_attribute,
    set_tag_attribute_values={
        "iframe": {
            "loading": "lazy",
            "referrerpolicy": "strict-origin-when-cross-origin",
            "sandbox": "allow-scripts allow-same-origin allow-presentation",
            "allow": "autoplay; encrypted-media; fullscreen; picture-in-picture",
        }
    },
    link_rel="noopener noreferrer",
    url_schemes={"http", "https", "mailto", "tel"},
    filter_style_properties=SAFE_STYLE_PROPERTIES,
)


def clean_rich_text(value: object) -> str:
    """Return a sanitized HTML fragment suitable for rendering in a page."""
    if value is None:
        return ""
    return _CLEANER.clean(str(value))
