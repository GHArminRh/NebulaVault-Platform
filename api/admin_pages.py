from functools import wraps

from django.http import HttpResponseForbidden


def admin_page_required(view_func):
    """Allow only active staff users to view API discovery/documentation pages.

    Unlike Django's staff_member_required decorator, this returns HTTP 403
    directly instead of redirecting anonymous visitors to the admin login.
    """
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        user = getattr(request, "user", None)
        if not (
            user
            and user.is_authenticated
            and user.is_active
            and user.is_staff
        ):
            response = HttpResponseForbidden(
                "403 Forbidden — دسترسی غیرمجاز. مشاهده این صفحه فقط برای مدیران مجاز است.",
                content_type="text/plain; charset=utf-8",
            )
            response["Cache-Control"] = "no-store"
            return response

        response = view_func(request, *args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        return response

    return wrapped
