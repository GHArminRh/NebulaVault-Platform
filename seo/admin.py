from django.contrib import admin

from .models import SEOAuditIssue, SEOAuditRun


class SEOAuditIssueInline(admin.TabularInline):
    model = SEOAuditIssue
    extra = 0
    can_delete = False
    fields = ("severity", "code", "url", "title", "recommendation")
    readonly_fields = fields
    show_change_link = True


@admin.register(SEOAuditRun)
class SEOAuditRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "pages_scanned",
        "issues_count",
        "created_at",
        "completed_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("error_message",)
    readonly_fields = (
        "status",
        "requested_by",
        "created_at",
        "started_at",
        "completed_at",
        "pages_scanned",
        "issues_count",
        "error_message",
    )
    inlines = (SEOAuditIssueInline,)
    date_hierarchy = "created_at"


@admin.register(SEOAuditIssue)
class SEOAuditIssueAdmin(admin.ModelAdmin):
    list_display = ("title", "severity", "code", "url", "run", "created_at")
    list_filter = ("severity", "code", "created_at")
    search_fields = ("title", "details", "url", "recommendation")
    readonly_fields = (
        "run",
        "url",
        "code",
        "severity",
        "title",
        "details",
        "recommendation",
        "created_at",
    )
    date_hierarchy = "created_at"
