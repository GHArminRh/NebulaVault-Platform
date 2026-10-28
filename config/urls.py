from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

from accounts.forms import NebulaAuthenticationForm
from accounts.views import CustomerLoginView
from config.admin_toggle import export_admin_object_json, import_admin_json, toggle_boolean_field
from portal.editor_uploads import editor_image_upload
from staff.admin_forms import AdminTurnstileAuthenticationForm

# Reuse the existing Django AdminSite and its Dracula theme, only replacing the
# login form so admin sign-in requires the same server-verified Turnstile check.
admin.site.login_form = AdminTurnstileAuthenticationForm


def service_worker(request):
    """Serve the PWA service worker from the site root so it controls all pages."""
    script = settings.BASE_DIR / "static" / "portal" / "service-worker.js"
    response = HttpResponse(
        script.read_text(encoding="utf-8"),
        content_type="application/javascript; charset=utf-8",
    )
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache"
    return response


def healthcheck(request):
    """Minimal Render health endpoint; avoids rendering the site or querying the database."""
    return HttpResponse("ok", content_type="text/plain")


urlpatterns = [
    path("healthz/", healthcheck, name="healthcheck"),
    path("service-worker.js", service_worker, name="service-worker"),
    path("admin/quick-toggle/", toggle_boolean_field, name="admin-quick-toggle"),
    path("admin/json-export/<str:app_label>/<str:model_name>/<str:object_id>/", export_admin_object_json, name="admin-json-export"),
    path("admin/json-import/<str:app_label>/<str:model_name>/", import_admin_json, name="admin-json-import"),
    path("admin/editor-upload/", editor_image_upload, name="editor-image-upload"),
    path("admin/", admin.site.urls),
    path("tinymce/", include("tinymce.urls")),
    path("comment/", include("comment.urls")),
    path("blog/", include("blog.urls")),
    path("api/licensing/", include("licensing.urls")),
    path("billing/", include("billing.urls")),
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
