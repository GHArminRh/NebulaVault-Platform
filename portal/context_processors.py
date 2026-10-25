def cart_context(request):
    """Expose cart count globally and license data only on the customer dashboard."""
    raw_ids = request.session.get("nebula_cart", [])
    if not isinstance(raw_ids, list):
        context = {"cart_count": 0}
    else:
        context = {"cart_count": len({str(value) for value in raw_ids if value})}

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
