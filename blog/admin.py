from django.contrib import admin, messages
from django.db.models import ImageField
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import ngettext
from image_uploader_widget.widgets import ImageUploaderWidget
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .forms import BlogPostAdminForm
from .models import BlogPost, BlogPostRating, Tag


def make_published(modeladmin, request, queryset):
    """Publish selected articles and initialize publication dates when needed."""
    queryset.filter(published_at__isnull=True).update(published_at=timezone.now())
    updated = queryset.update(status=BlogPost.Status.PUBLISHED)
    modeladmin.message_user(
        request,
        ngettext(
            "%d story was successfully marked as published.",
            "%d stories were successfully marked as published.",
            updated,
        ) % updated,
        messages.SUCCESS,
    )


make_published.short_description = "Publish selected articles"


def make_drafted(modeladmin, request, queryset):
    updated = queryset.update(status=BlogPost.Status.DRAFT)
    modeladmin.message_user(
        request,
        ngettext(
            "%d story was successfully marked as draft.",
            "%d stories were successfully marked as drafts.",
            updated,
        ) % updated,
        messages.SUCCESS,
    )


make_drafted.short_description = "Move selected articles to drafts"


class MembershipInline(admin.TabularInline):
    model = BlogPost.tags.through
    extra = 0
    verbose_name = "Article membership"
    verbose_name_plural = "Articles using this tag"


class TagResource(resources.ModelResource):
    class Meta:
        model = Tag
        fields = ("id", "name")
        export_order = ("id", "name")
        import_id_fields = ("id",)


class BlogPostResource(resources.ModelResource):
    class Meta:
        model = BlogPost
        fields = (
            "uuid",
            "title",
            "slug",
            "excerpt",
            "content",
            "category",
            "status",
            "is_featured",
            "published_at",
            "seo_title",
            "seo_description",
        )
        export_order = fields
        import_id_fields = ("slug",)


@admin.register(Tag)
class TagAdmin(ImportExportModelAdmin):
    resource_classes = (TagResource,)
    inlines = (MembershipInline,)
    list_display = ("name", "post_count")
    search_fields = ("name",)
    ordering = ("name",)
    list_per_page = 25

    @admin.display(description="Article count")
    def post_count(self, obj):
        return obj.posts.count()


@admin.register(BlogPost)
class BlogPostAdmin(ImportExportModelAdmin):
    form = BlogPostAdminForm
    resource_classes = (BlogPostResource,)
    formfield_overrides = {ImageField: {"widget": ImageUploaderWidget}}
    list_display = (
        "title",
        "show_post",
        "created_at",
        "updated_at",
        "status",
        "display_tags",
        "delete_link",
    )
    list_filter = ("status", "is_featured", "category", "tags", "published_at")
    list_per_page = 4
    readonly_fields = ("uuid", "created_at", "updated_at", "published_at")
    date_hierarchy = "created_at"
    empty_value_display = "-"
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("status", "published_at")
    actions = (make_published, make_drafted)
    filter_horizontal = ("tags",)
    search_fields = ("title", "slug", "excerpt", "tags__name")
    save_on_top = True
    fieldsets = (
        ("Header", {"fields": (("title", "slug"), "excerpt", "category")}),
        ("Body", {"fields": ("content", "img")}),
        ("Tags", {"classes": ("collapse",), "fields": ("tags",)}),
        (
            "Dates",
            {
                "classes": ("collapse",),
                "fields": ("created_at", "updated_at", "published_at"),
            },
        ),
        ("Publishing", {"fields": ("status", "is_featured")}),
        (
            "Search engines",
            {
                "classes": ("collapse",),
                "fields": ("seo_title", "seo_description"),
            },
        ),
        (
            "Identifiers",
            {"classes": ("collapse",), "fields": ("uuid",)},
        ),
    )

    @admin.display(description="Public article", ordering="slug")
    def show_post(self, obj):
        if obj.status != BlogPost.Status.PUBLISHED:
            return "-"
        url = reverse("blog:post_detail", kwargs={"slug": obj.slug})
        return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', url, obj.slug)

    @admin.display(description="Tags")
    def display_tags(self, obj):
        names = list(obj.tags.order_by("name").values_list("name", flat=True)[:3])
        if not names:
            return "-"
        result = ", ".join(names)
        if obj.tags.count() > 3:
            result += ", …"
        return result

    @admin.display(description="Delete", boolean=False)
    def delete_link(self, obj):
        url = reverse(
            f"admin:{obj._meta.app_label}_{obj._meta.model_name}_delete",
            args=(obj.pk,),
        )
        return format_html('<a class="button" href="{}">Delete</a>', url)

    def save_model(self, request, obj, form, change):
        if obj.status == BlogPost.Status.PUBLISHED and not obj.published_at:
            obj.published_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(BlogPostRating)
class BlogPostRatingAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "score", "updated_at")
    list_filter = ("score", "updated_at")
    search_fields = ("post__title", "user__email")
    readonly_fields = ("created_at", "updated_at")
