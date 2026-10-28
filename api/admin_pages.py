from functools import wraps

from django.shortcuts import render


def admin_page_required(view_func):
    """Restrict API discovery and documentation pages to active staff users.

    Return a branded HTTP 403 page directly, without redirecting API clients
    or anonymous visitors to the Django admin login.
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
            response = render(request, "errors/403.html", status=403)
            response["Cache-Control"] = "no-store"
            response["X-Robots-Tag"] = "noindex, nofollow"
            return response

        response = view_func(request, *args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response

    return wrapped
