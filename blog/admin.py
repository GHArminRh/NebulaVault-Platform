from django.contrib import admin
from django.utils import timezone

from .forms import BlogPostAdminForm
from .models import BlogPost, BlogPostRating, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "post_count")
    search_fields = ("name",)
    ordering = ("name",)

    @admin.display(description="تعداد مقاله‌ها")
    def post_count(self, obj):
        return obj.posts.count()


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    form = BlogPostAdminForm
    list_display = ("title", "category", "status", "is_featured", "published_at", "updated_at")
    list_filter = ("status", "is_featured", "category", "tags", "published_at")
    search_fields = ("title", "excerpt", "content", "tags__name")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("uuid", "created_at", "updated_at")
    filter_horizontal = ("tags",)
    date_hierarchy = "published_at"
    list_per_page = 25
    save_on_top = True
    fieldsets = (
        ("Article", {"fields": ("title", "slug", "excerpt", "content", "img", "category", "tags")}),
        ("Publishing", {"fields": ("status", "is_featured", "published_at")}),
        ("Search engines", {"classes": ("collapse",), "fields": ("seo_title", "seo_description")}),
        ("Identifiers and timestamps", {"classes": ("collapse",), "fields": ("uuid", "created_at", "updated_at")}),
    )

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
