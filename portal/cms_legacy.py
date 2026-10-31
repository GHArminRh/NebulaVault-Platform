"""Conservative conversion of legacy rich-text homepage sections."""

from html.parser import HTMLParser

from django.core.exceptions import ValidationError
from django.db import transaction

from cms.api import add_plugin
from cms.models import Placeholder
from cms.models.pluginmodel import CMSPlugin

from .models import validate_cms_link


_VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


class _Node:
    def __init__(self, tag, attrs=None):
        self.tag = tag
        self.attrs = dict(attrs or ())
        self.children = []

    def classes(self):
        return set(self.attrs.get("class", "").split())


class _TreeBuilder(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.root = _Node("root")
        self.stack = [self.root]
        self.feed(source or "")
        self.close()

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in _VOID_ELEMENTS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(_Node(tag, attrs))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _walk(node):
    for child in node.children:
        if isinstance(child, _Node):
            yield child
            yield from _walk(child)


def _text(node, excluded_classes=(), excluded_tags=()):
    if node is None:
        return ""
    parts = []
    for child in node.children:
        if isinstance(child, str):
            parts.append(child)
            continue
        if child.tag == "br":
            parts.append("\n")
            continue
        if child.tag in excluded_tags or child.classes().intersection(excluded_classes):
            continue
        parts.append(_text(child, excluded_classes, excluded_tags))
    return "".join(parts)


def _clean(value):
    return " ".join((value or "").replace("\xa0", " ").split()).strip()


def _first(root, *, tag=None, class_name=None):
    for node in _walk(root):
        if tag and node.tag != tag:
            continue
        if class_name and class_name not in node.classes():
            continue
        return node
    return None


def _safe_link(value):
    value = (value or "").strip()
    if not value:
        return ""
    try:
        validate_cms_link(value)
    except ValidationError:
        return ""
    return value


def parse_hero(source):
    root = _TreeBuilder(source).root
    nodes = list(_walk(root))
    heading_node = next((node for node in nodes if node.tag == "h1"), None)
    if heading_node is None:
        return None

    accent_node = next(
        (node for node in _walk(heading_node) if "gradient-text" in node.classes()),
        None,
    )
    if accent_node is not None:
        heading = _clean(_text(heading_node, {"gradient-text"}))
        accent = _clean(_text(accent_node))
    else:
        pieces = _text(heading_node).split("\n", 1)
        heading = _clean(pieces[0])
        accent = _clean(pieces[1]) if len(pieces) > 1 else ""

    eyebrow_node = next((node for node in nodes if "eyebrow" in node.classes()), None)
    paragraphs = [node for node in nodes if node.tag == "p"]
    heading_position = nodes.index(heading_node)
    description = ""
    for paragraph in paragraphs:
        if nodes.index(paragraph) > heading_position and not any(
            child.tag == "a" for child in _walk(paragraph)
        ):
            description = _clean(_text(paragraph))
            if description:
                break

    if eyebrow_node:
        eyebrow = _clean(_text(eyebrow_node))
    else:
        eyebrow = _clean(_text(paragraphs[0])) if paragraphs else ""

    links = [
        node for node in nodes
        if node.tag == "a" and _clean(_text(node)) and _safe_link(node.attrs.get("href"))
    ]
    trust_node = next((node for node in nodes if "nv-hero-trust" in node.classes()), None)
    trust_items = (
        [_clean(_text(node)) for node in _walk(trust_node) if node.tag == "span"]
        if trust_node else []
    )
    trust_items = [item for item in trust_items if item]
    if not trust_items and paragraphs:
        candidate = _clean(_text(paragraphs[-1]))
        if candidate and ("◇" in candidate or "⌁" in candidate):
            trust_items = [_clean(item) for item in candidate.replace("⌁", "◇").split("◇")]
            trust_items = [item for item in trust_items if item]

    payload = {
        "eyebrow": eyebrow or "فضای دیجیتال شما، با نظم تازه",
        "heading": heading,
        "heading_accent": accent,
        "description": description,
        "primary_cta_label": _clean(_text(links[0])) if links else "کشف محصولات ↙",
        "primary_cta_url": _safe_link(links[0].attrs.get("href")) if links else "/products/",
        "secondary_cta_label": _clean(_text(links[1])) if len(links) > 1 else "مشاهده تعرفه‌ها ↗",
        "secondary_cta_url": _safe_link(links[1].attrs.get("href")) if len(links) > 1 else "/pricing/",
        "trust_item_1": trust_items[0] if trust_items else "حساب شخصی امن",
        "trust_item_2": trust_items[1] if len(trust_items) > 1 else "خرید و لایسنس یکپارچه",
        "trust_item_3": trust_items[2] if len(trust_items) > 2 else "تجربهٔ هماهنگ",
        "legacy_source": source or "",
    }
    return payload if heading else None


def parse_features(source):
    root = _TreeBuilder(source).root
    grid = next((node for node in _walk(root) if "nv-feature-grid" in node.classes()), None)
    if grid is None:
        return None
    cards = [
        node for node in _walk(grid)
        if node.tag == "article" and "nv-feature-card" in node.classes()
    ]
    if not cards:
        return None

    payload = {"legacy_source": source or ""}
    for index, card in enumerate(cards[:3], start=1):
        nodes = list(_walk(card))
        icon = next((node for node in nodes if "nv-feature-icon" in node.classes()), None)
        number = next((node for node in nodes if "nv-feature-number" in node.classes()), None)
        heading = next((node for node in nodes if node.tag == "h3"), None)
        description = next((node for node in nodes if node.tag == "p"), None)
        link = next((node for node in nodes if node.tag == "a"), None)
        payload.update({
            f"feature_{index}_icon": _clean(_text(icon)) if icon else "",
            f"feature_{index}_number": _clean(_text(number)) if number else f"0{index}",
            f"feature_{index}_title": _clean(_text(heading)) if heading else "",
            f"feature_{index}_description": _clean(_text(description)) if description else "",
            f"feature_{index}_link_label": _clean(_text(link)) if link else "",
            f"feature_{index}_link_url": _safe_link(link.attrs.get("href")) if link else "",
        })
    for index in range(len(cards) + 1, 4):
        payload.update({
            f"feature_{index}_icon": "",
            f"feature_{index}_number": f"0{index}",
            f"feature_{index}_title": "",
            f"feature_{index}_description": "",
            f"feature_{index}_link_label": "",
            f"feature_{index}_link_url": "",
        })
    return payload


def parse_faq(source):
    root = _TreeBuilder(source).root
    faq = next((node for node in _walk(root) if "nv-faq-list" in node.classes()), None)
    if faq is None:
        return None
    entries = [node for node in _walk(faq) if node.tag == "details"]
    if not entries:
        return None

    payload = {"legacy_source": source or ""}
    for index, entry in enumerate(entries[:3], start=1):
        nodes = list(_walk(entry))
        summary = next((node for node in nodes if node.tag == "summary"), None)
        answer = next((node for node in nodes if node.tag == "p"), None)
        payload[f"question_{index}"] = _clean(_text(summary, excluded_tags={"span"})) if summary else ""
        payload[f"answer_{index}"] = _clean(_text(answer)) if answer else ""
    for index in range(len(entries) + 1, 4):
        payload[f"question_{index}"] = ""
        payload[f"answer_{index}"] = ""
    return payload


def convert_legacy_homepage_sections(page_content):
    """Convert only recognized, single root TextPlugins without nested plugins."""
    converted = []
    errors = []
    converters = {
        "hero": ("HeroContentPlugin", parse_hero),
        "features": ("FeatureGridPlugin", parse_features),
        "about": ("FAQListPlugin", parse_faq),
    }
    placeholders = {
        placeholder.slot: placeholder
        for placeholder in Placeholder.objects.get_for_obj(page_content)
    }

    for slot, (plugin_type, parser) in converters.items():
        placeholder = placeholders.get(slot)
        if placeholder is None:
            continue
        roots = CMSPlugin.objects.filter(
            placeholder_id=placeholder.pk,
            language=page_content.language,
            parent__isnull=True,
        ).order_by("position", "pk")
        if roots.count() != 1:
            continue
        old = roots.first()
        if old.plugin_type != "TextPlugin" or CMSPlugin.objects.filter(parent_id=old.pk).exists():
            continue

        try:
            legacy_instance, _plugin_class = old.get_plugin_instance()
            source = getattr(legacy_instance, "body", "")
            if not source:
                continue
            payload = parser(source)
            if payload is None:
                continue

            with transaction.atomic():
                new_plugin = add_plugin(
                    placeholder,
                    plugin_type,
                    page_content.language,
                    **payload,
                )
                old_queryset = CMSPlugin.objects.filter(pk=old.pk)
                if hasattr(placeholder, "delete_plugins"):
                    placeholder.delete_plugins(old_queryset)
                elif hasattr(placeholder, "delete_plugin"):
                    placeholder.delete_plugin(old_queryset.get())
                else:
                    old_queryset.delete()
                converted.append((slot, new_plugin.pk))
        except Exception as exc:  # Preserve the source plugin if conversion fails.
            errors.append((slot, exc.__class__.__name__))

    return converted, errors
