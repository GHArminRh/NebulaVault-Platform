from django.shortcuts import render


class AdminOnlyV1ApiMiddleware:
    """Restrict every versioned API route to active staff, with a branded 403 page.

    This deliberately does not cover /api/licensing/, which is used by the
    desktop application's license activation and validation workflow.
    """

    API_PREFIXES = ("/api/v1/", "/api/v1")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path_info.startswith(self.API_PREFIXES):
            user = getattr(request, "user", None)
            if not (
                user
                and user.is_authenticated
                and user.is_active
                and user.is_staff
            ):
                response = render(
                    request,
                    "errors/403.html",
                    status=403,
                )
                response["Cache-Control"] = "no-store"
                response["X-Robots-Tag"] = "noindex, nofollow"
                return response

        response = self.get_response(request)
        if request.path_info.startswith(self.API_PREFIXES):
            response["Cache-Control"] = "private, no-store"
        return response
