"""Template filters for consistent public-site navigation ordering."""

from django import template

register = template.Library()


@register.filter
def blog_before_releases(links):
    """Move the blog link directly before the releases link, preserving other links."""
    ordered_links = list(links or [])

    def link_kind(item):
        value = getattr(item, "value", {})
        label = str(value.get("label", "")).strip().casefold()
        url = str(value.get("url", "")).strip().casefold()

        if "blog" in label or "بلاگ" in label or url.endswith("#blog"):
            return "blog"
        if (
            "version" in label
            or "release" in label
            or "نسخه" in label
            or url.endswith("#releases")
        ):
            return "releases"
        return None

    blog_index = next(
        (index for index, item in enumerate(ordered_links) if link_kind(item) == "blog"),
        None,
    )
    releases_index = next(
        (index for index, item in enumerate(ordered_links) if link_kind(item) == "releases"),
        None,
    )

    if blog_index is not None and releases_index is not None and blog_index > releases_index:
        blog_link = ordered_links.pop(blog_index)
        ordered_links.insert(releases_index, blog_link)

    return ordered_links
