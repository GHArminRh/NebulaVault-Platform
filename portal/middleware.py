"""Force a consistent Persian interface across the public site."""
from django.core.exceptions import ValidationError
from django.utils.deprecation import MiddlewareMixin
from django.utils import translation

LANGUAGE_COOKIE = "nv_language"
COOKIE_MAX_AGE = 60 * 60 * 24 * 180


class InterfaceLanguageMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Keep Django admin in English while the public-facing site stays Persian.
        is_admin = request.path == "/admin" or request.path.startswith("/admin/")
        language = "en-us" if is_admin else "fa"
        translation.activate(language)
        request.LANGUAGE_CODE = language
        request.site_language = "en" if is_admin else "fa"
        request.language_was_selected = True
        return None

    def process_response(self, request, response):
        # Never persist the public Persian preference on admin responses.
        if request.path == "/admin" or request.path.startswith("/admin/"):
            return response
        response.set_cookie(
            LANGUAGE_COOKIE, "fa", max_age=COOKIE_MAX_AGE,
            samesite="Lax", secure=request.is_secure(), httponly=False,
        )
        return response


class SeparateStaffAndCustomerSessionsMiddleware(MiddlewareMixin):
    """Restrict staff identities to the admin interface."""

    def process_request(self, request):
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import AnonymousUser
        from django.shortcuts import redirect

        if request.path == "/admin" or request.path.startswith("/admin/"):
            return None
        user = getattr(request, "user", None)
        try:
            is_authenticated = bool(user and user.is_authenticated)
        except (ValidationError, ValueError, TypeError):
            request.session.flush()
            request.user = AnonymousUser()
            return None

        if not is_authenticated:
            return None
        if isinstance(user, get_user_model()):
            if request.path.rstrip("/") == "/accounts/logout":
                return redirect("portal:home")
            # The CMS frontend editor needs the staff identity on CMS pages only.
            # Keep the existing staff/customer session separation everywhere else.
            staff_only_frontend_paths = {
                "/api",
                "/api/",
                "/api/v1/",
                "/api/v1/schema/",
                "/api/v1/docs/",
            }
            if (
                getattr(user, "is_staff", False)
                and (
                    request.path.startswith("/pages/")
                    or (
                        request.path == "/"
                        and getattr(request, "current_page", None) is not None
                    )
                    or request.path in staff_only_frontend_paths
                )
            ):
                return None
            request.user = AnonymousUser()
        return None
