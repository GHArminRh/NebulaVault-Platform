from django.contrib import admin
from django.utils import timezone
from .forms import BlogPostAdminForm
from .models import BlogPost
@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    form = BlogPostAdminForm
    list_display = ("title", "category", "status", "is_featured", "published_at", "updated_at")
    list_filter = ("status", "is_featured", "category", "published_at")
    search_fields = ("title", "excerpt", "content", "tags")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "published_at"
    list_per_page = 25
    save_on_top = True
    fieldsets = (
        ("Article", {"fields": ("title", "slug", "excerpt", "content", "cover_image", "category", "tags")}),
        ("Publishing", {"fields": ("status", "is_featured", "published_at")}),
        ("Search engines", {"classes": ("collapse",), "fields": ("seo_title", "seo_description")}),
        ("Timestamps", {"classes": ("collapse",), "fields": ("created_at", "updated_at")}),
    )
    def save_model(self, request, obj, form, change):
        if obj.status == BlogPost.Status.PUBLISHED and not obj.published_at: obj.published_at = timezone.now()
        super().save_model(request, obj, form, change)
