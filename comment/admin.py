from django.contrib import admin, messages
from django.utils.translation import ngettext
from .models import Comment, CommentSettings, React, Reaction

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("content_main", "user", "status", "status_edited", "is_pinned", "posted", "content_object")
    list_filter = ("status", "status_edited", "is_pinned", "is_spoiler", "posted")
    search_fields = ("content_main", "content", "user__email")
    readonly_fields = ("user","content_main","content","parent","content_type","object_id","urlhash","posted","updated")
    actions = ("accept_comments","reject_comments","pin_comments","unpin_comments")
    @admin.action(description="Accept selected comments")
    def accept_comments(self, request, queryset):
        count=queryset.update(status="a")
        self.message_user(request,ngettext("%d comment accepted.","%d comments accepted.",count)%count,messages.SUCCESS)
    @admin.action(description="Reject selected comments")
    def reject_comments(self, request, queryset):
        count=queryset.update(status="r")
        self.message_user(request,ngettext("%d comment rejected.","%d comments rejected.",count)%count,messages.WARNING)
    @admin.action(description="Pin selected comments")
    def pin_comments(self, request, queryset): queryset.update(is_pinned=True)
    @admin.action(description="Unpin selected comments")
    def unpin_comments(self, request, queryset): queryset.update(is_pinned=False)

@admin.register(CommentSettings)
class CommentSettingsAdmin(admin.ModelAdmin):
    list_display=("name","slug","status_check","allow_reply","allow_edit","allow_delete")
    fieldsets=((None,{"fields":("name","slug","content_words_count","per_page","theme_direction","theme_dark_mode")}),("Moderation",{"fields":("status_check","status_edited_check")}),("Features",{"fields":("allow_spoiler","allow_reply","allow_edit","allow_delete","allow_reaction")}))

@admin.register(React)
class ReactAdmin(admin.ModelAdmin):
    list_display=("slug","emoji")
    search_fields=("slug","emoji")

@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display=("user","comment","react")
    readonly_fields=("user","comment","react")
