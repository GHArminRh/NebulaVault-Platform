from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from accounts.forms import NebulaAuthenticationForm
from accounts.views import CustomerLoginView
from config.admin_toggle import export_admin_object_json, import_admin_json, toggle_boolean_field
from portal.editor_uploads import editor_image_upload

urlpatterns = [
    path("admin/quick-toggle/", toggle_boolean_field, name="admin-quick-toggle"),
    path("admin/json-export/<str:app_label>/<str:model_name>/<str:object_id>/", export_admin_object_json, name="admin-json-export"),
    path("admin/json-import/<str:app_label>/<str:model_name>/", import_admin_json, name="admin-json-import"),
    path("admin/editor-upload/", editor_image_upload, name="editor-image-upload"),
    path("admin/", admin.site.urls),
    path("api/licensing/", include("licensing.urls")),
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
