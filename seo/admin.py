from django.contrib import admin

from .models import SEOAuditIssue, SEOAuditRun, SearchConsoleConnection, SearchConsoleMetric


# The dedicated dashboard is linked from the audit-run changelist.


class SEOAuditIssueInline(admin.TabularInline):
    model = SEOAuditIssue
    extra = 0
    can_delete = False
    fields = ("severity", "code", "url", "title", "recommendation")
    readonly_fields = fields
    show_change_link = True


@admin.register(SEOAuditRun)
class SEOAuditRunAdmin(admin.ModelAdmin):
    change_list_template = "admin/seo/seoauditrun/change_list.html"
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


@admin.register(SearchConsoleConnection)
class SearchConsoleConnectionAdmin(admin.ModelAdmin):
    list_display = ("site_url", "is_active", "connected_at", "last_synced_at")
    readonly_fields = ("site_url", "connected_email", "refresh_token_encrypted", "granted_scope", "connected_at", "last_synced_at", "last_sync_error")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SearchConsoleMetric)
class SearchConsoleMetricAdmin(admin.ModelAdmin):
    list_display = ("date", "dimension_type", "dimension_value", "clicks", "impressions", "position")
    list_filter = ("dimension_type", "date")
    search_fields = ("dimension_value",)
    readonly_fields = ("connection", "date", "dimension_type", "dimension_value", "clicks", "impressions", "ctr", "position", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
