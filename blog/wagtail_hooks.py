from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.admin.rich_text.editors.draftail import DraftailRichTextArea
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import BlogPost, Tag


BLOG_RICH_TEXT_FEATURES = [
    "h2",
    "h3",
    "bold",
    "italic",
    "link",
    "ul",
    "ol",
    "blockquote",
    "hr",
]


class BlogPostViewSet(SnippetViewSet):
    model = BlogPost
    icon = "doc-full"
    menu_label = "مقالات وبلاگ"
    menu_name = "blog-posts"
    add_to_admin_menu = True
    list_display = (
        "title",
        "status",
        "category",
        "is_featured",
        "published_at",
        "updated_at",
    )
    search_fields = ("title", "slug", "excerpt", "content")
    list_per_page = 20
    panels = [
        FieldPanel("title"),
        FieldPanel("slug"),
        FieldPanel("excerpt"),
        FieldPanel(
            "content",
            widget=DraftailRichTextArea(features=BLOG_RICH_TEXT_FEATURES),
        ),
        MultiFieldPanel(
            [
                FieldPanel("category"),
                FieldPanel("tags"),
                FieldPanel("img"),
            ],
            heading="دسته‌بندی و رسانه",
        ),
        MultiFieldPanel(
            [
                FieldPanel("status"),
                FieldPanel("is_featured"),
                FieldPanel("published_at"),
            ],
            heading="انتشار",
        ),
        MultiFieldPanel(
            [
                FieldPanel("seo_title"),
                FieldPanel("seo_description"),
            ],
            heading="بهینه‌سازی موتور جست‌وجو",
        ),
    ]


class BlogTagViewSet(SnippetViewSet):
    model = Tag
    icon = "tag"
    menu_label = "برچسب‌های وبلاگ"
    menu_name = "blog-tags"
    add_to_admin_menu = True
    list_display = ("name",)
    search_fields = ("name",)
    panels = [FieldPanel("name")]


register_snippet(BlogPostViewSet)
register_snippet(BlogTagViewSet)
