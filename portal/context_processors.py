from django.conf import settings


def cart_context(request):
    """Expose cart count and safe payment-mode flags globally."""
    raw_ids = request.session.get("nebula_cart", [])
    if not isinstance(raw_ids, list):
        context = {"cart_count": 0}
    else:
        context = {"cart_count": len({str(value) for value in raw_ids if value})}

    context["local_payment_simulator_enabled"] = bool(
        settings.DEBUG and getattr(settings, "NEBULA_MOCK_PAYMENTS", False)
    )
    context["zarinpal_merchant_configured"] = bool(
        getattr(settings, "ZARINPAL_MERCHANT_ID", "").strip()
    )

    if (
        getattr(request, "user", None)
        and request.user.is_authenticated
        and request.path.rstrip("/").endswith("/dashboard")
    ):
        from licensing.models import License
        context["dashboard_licenses"] = (
            License.objects.filter(subscription__user=request.user)
            .select_related("subscription", "subscription__product", "subscription__plan")
            .order_by("-created_at")
        )
    else:
        context["dashboard_licenses"] = ()
    return context
