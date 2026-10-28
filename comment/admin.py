from django.contrib import admin, messages
from django.utils.translation import ngettext
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import Comment, CommentSettings, React, Reaction


class CommentSettingsResource(resources.ModelResource):
    class Meta:
        model = CommentSettings
        fields = ("slug", "name", "content_words_count", "status_check", "status_edited_check", "allow_spoiler", "allow_reply", "allow_edit", "allow_delete", "allow_reaction", "per_page", "theme_direction", "theme_dark_mode")
        export_order = fields
        import_id_fields = ("slug",)


class ReactResource(resources.ModelResource):
    class Meta:
        model = React
        fields = ("slug", "emoji")
        export_order = fields
        import_id_fields = ("slug",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("content_main", "user", "status", "status_edited", "is_pinned", "posted", "content_object")
    list_filter = ("status", "status_edited", "is_pinned", "is_spoiler", "posted")
    search_fields = ("content_main", "content", "user__email")
    readonly_fields = ("user", "content_main", "content", "parent", "content_type", "object_id", "urlhash", "posted", "updated")
    actions = ("accept_comments", "reject_comments", "accept_edits", "reject_edits", "pin_comments", "unpin_comments")

    @admin.action(description="Accept selected comments")
    def accept_comments(self, request, queryset):
        count = queryset.update(status="a")
        self.message_user(request, ngettext("%d comment accepted.", "%d comments accepted.", count) % count, messages.SUCCESS)

    @admin.action(description="Reject selected comments")
    def reject_comments(self, request, queryset):
        count = queryset.update(status="r")
        self.message_user(request, ngettext("%d comment rejected.", "%d comments rejected.", count) % count, messages.WARNING)

    @admin.action(description="Accept selected comment edits")
    def accept_edits(self, request, queryset):
        for comment in queryset.filter(status_edited="d"):
            comment.content_main = comment.content
            comment.status_edited = "a"
            comment.save(update_fields=("content_main", "status_edited", "updated"))

    @admin.action(description="Reject selected comment edits")
    def reject_edits(self, request, queryset):
        for comment in queryset.filter(status_edited="d"):
            comment.content = comment.content_main
            comment.status_edited = "r"
            comment.save(update_fields=("content", "status_edited", "updated"))

    @admin.action(description="Pin selected comments")
    def pin_comments(self, request, queryset):
        queryset.update(is_pinned=True)

    @admin.action(description="Unpin selected comments")
    def unpin_comments(self, request, queryset):
        queryset.update(is_pinned=False)


@admin.register(CommentSettings)
class CommentSettingsAdmin(ImportExportModelAdmin):
    resource_classes = (CommentSettingsResource,)
    list_display = ("name", "slug", "status_check", "allow_reply", "allow_edit", "allow_delete")
    fieldsets = (
        (None, {"fields": ("name", "slug", "content_words_count", "per_page", "theme_direction", "theme_dark_mode")}),
        ("Moderation", {"fields": ("status_check", "status_edited_check")}),
        ("Features", {"fields": ("allow_spoiler", "allow_reply", "allow_edit", "allow_delete", "allow_reaction")}),
    )


@admin.register(React)
class ReactAdmin(ImportExportModelAdmin):
    resource_classes = (ReactResource,)
    list_display = ("slug", "emoji")
    search_fields = ("slug", "emoji")


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ("user", "comment", "react")
    readonly_fields = ("user", "comment", "react")
    has_add_permission = lambda self, request: False
    has_change_permission = lambda self, request, obj=None: False
    has_delete_permission = lambda self, request, obj=None: False
