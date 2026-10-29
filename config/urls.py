from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.shortcuts import render
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

from api.admin_pages import admin_page_required

from accounts.forms import NebulaAuthenticationForm
from accounts.views import CustomerLoginView
from config.admin_toggle import toggle_boolean_field
from portal.editor_uploads import editor_image_upload
from staff.admin_forms import AdminTurnstileAuthenticationForm

admin.site.login_form = AdminTurnstileAuthenticationForm


def service_worker(request):
    script = settings.BASE_DIR / "static" / "portal" / "service-worker.js"
    response = HttpResponse(
        script.read_text(encoding="utf-8"),
        content_type="application/javascript; charset=utf-8",
    )
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache"
    return response


def healthcheck(request):
    return HttpResponse("ok", content_type="text/plain")


@admin_page_required
def api_index(request):
    """Private API route directory for authenticated staff members."""
    endpoints = [
        {"method": "GET", "path": "/api/v1/", "auth": "مدیر فعال", "description": "وضعیت و اطلاعات پایه API"},
        {"method": "GET", "path": "/api/v1/products/", "auth": "عمومی", "description": "فهرست محصولات فعال"},
        {"method": "GET", "path": "/api/v1/products/{slug}/", "auth": "عمومی", "description": "جزئیات محصول"},
        {"method": "GET", "path": "/api/v1/releases/", "auth": "عمومی", "description": "نسخه‌های منتشرشده"},
        {"method": "GET", "path": "/api/v1/releases/{id}/", "auth": "عمومی", "description": "جزئیات نسخه"},
        {"method": "GET", "path": "/api/v1/plans/", "auth": "عمومی", "description": "طرح‌های فعال خرید"},
        {"method": "GET", "path": "/api/v1/plans/{id}/", "auth": "عمومی", "description": "جزئیات طرح"},
        {"method": "GET", "path": "/api/v1/blog/posts/", "auth": "عمومی", "description": "مقالات منتشرشده"},
        {"method": "GET", "path": "/api/v1/blog/posts/{slug}/", "auth": "عمومی", "description": "جزئیات مقاله"},
        {"method": "GET", "path": "/api/v1/blog/tags/", "auth": "عمومی", "description": "برچسب‌های وبلاگ"},
        {"method": "GET", "path": "/api/v1/blog/tags/{id}/", "auth": "عمومی", "description": "جزئیات برچسب"},
        {"method": "GET", "path": "/api/v1/blog/posts/{slug}/rating/", "auth": "GET عمومی؛ تغییر امتیاز با توکن", "description": "مشاهده خلاصه امتیاز مقاله"},
        {"method": "POST", "path": "/api/v1/blog/posts/{slug}/rating/", "auth": "توکن مشتری", "description": "ثبت یا ویرایش امتیاز مقاله"},
        {"method": "POST", "path": "/api/v1/auth/token/", "auth": "ایمیل و گذرواژه مشتری", "description": "صدور توکن دسترسی مشتری"},
        {"method": "POST", "path": "/api/v1/auth/token/revoke/", "auth": "توکن Bearer", "description": "لغو توکن فعلی"},
        {"method": "GET / PATCH / PUT", "path": "/api/v1/account/me/", "auth": "توکن مشتری یا نشست مشتری", "description": "مشاهده و ویرایش اطلاعات مجاز حساب"},
        {"method": "GET", "path": "/api/v1/account/subscriptions/", "auth": "توکن مشتری یا نشست مشتری", "description": "اشتراک‌های حساب فعلی"},
        {"method": "GET", "path": "/api/v1/account/orders/", "auth": "توکن مشتری یا نشست مشتری", "description": "سفارش‌های حساب فعلی"},
        {"method": "GET", "path": "/api/v1/account/licenses/", "auth": "توکن مشتری یا نشست مشتری", "description": "لایسنس‌ها و اطلاعات امن فعال‌سازی حساب فعلی"},
        {"method": "GET", "path": "/api/v1/schema/", "auth": "مدیر فعال", "description": "طرح OpenAPI"},
        {"method": "GET", "path": "/api/v1/docs/", "auth": "مدیر فعال", "description": "مستندات تعاملی Swagger"},
        {"method": "POST", "path": "/api/licensing/activate/", "auth": "کلاینت دسکتاپ", "description": "فعال‌سازی لایسنس دسکتاپ (مسیر سازگاری قبلی)"},
        {"method": "POST", "path": "/api/licensing/validate/", "auth": "کلاینت دسکتاپ", "description": "اعتبارسنجی لایسنس دسکتاپ (مسیر سازگاری قبلی)"},
        {"method": "POST", "path": "/api/licensing/deactivate/", "auth": "کلاینت دسکتاپ", "description": "غیرفعال‌سازی لایسنس دسکتاپ (مسیر سازگاری قبلی)"},
    ]
    response = render(request, "admin/api_index.html", {"endpoints": endpoints})
    response["Cache-Control"] = "private, no-store"
    return response


urlpatterns = [
    path("healthz/", healthcheck, name="healthcheck"),
    path("service-worker.js", service_worker, name="service-worker"),
    path("admin/quick-toggle/", toggle_boolean_field, name="admin-quick-toggle"),
    path("admin/editor-upload/", editor_image_upload, name="editor-image-upload"),
    # Django Control Room endpoints must be registered before the admin catch-all.
    path("admin/dj-control-room-base/", include("dj_control_room_base.urls")),
    path("admin/dj-redis-panel/", include("dj_redis_panel.urls")),
    path("admin/dj-cache-panel/", include("dj_cache_panel.urls")),
    path("admin/dj-celery-panel/", include("dj_celery_panel.urls")),
    path("admin/dj-urls-panel/", include("dj_urls_panel.urls")),
    path("admin/dj-signals-panel/", include("dj_signals_panel.urls")),
    path("admin/dj-error-panel/", include("dj_error_panel.urls")),
    path("admin/dj-control-room/", include("dj_control_room.urls")),
    path("admin/", admin.site.urls),
    path("api", api_index, name="admin-api-index"),
    path("api/", api_index, name="admin-api-index-slash"),
    path("tinymce/", include("tinymce.urls")),
    path("comment/", include("comment.urls")),
    path("blog/", include("blog.urls")),
    path("api/v1/", include("api.urls")),
    path("api/licensing/", include("licensing.urls")),
    path("billing/", include("billing.urls")),
    # CMS pages are isolated under /pages/ to preserve all existing routes.
    path("pages/", include("cms.urls")),
    path(
        "accounts/login/",
        CustomerLoginView.as_view(
            template_name="portal/login.html",
            authentication_form=NebulaAuthenticationForm,
        ),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/", include("accounts.urls")),
    path("", include("portal.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
