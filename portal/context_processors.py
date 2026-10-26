from collections import defaultdict

from catalog.models import Plan


def cart_context(request):
    """Expose the cart count and a compact, validated cart preview site-wide."""
    raw_ids = request.session.get("nebula_cart", [])
    if not isinstance(raw_ids, list):
        plan_ids = []
    else:
        plan_ids = list(dict.fromkeys(str(value) for value in raw_ids if value))

    plans = list(
        Plan.objects.filter(
            pk__in=plan_ids,
            is_active=True,
            product__is_active=True,
        ).select_related("product")
    ) if plan_ids else []
    totals = defaultdict(int)
    for plan in plans:
        totals[plan.currency] += plan.price_minor_units

    context = {
        "cart_count": len(plans),
        "cart_preview_plans": plans[:4],
        "cart_preview_totals": [
            {"currency": currency, "amount_minor_units": amount}
            for currency, amount in sorted(totals.items())
        ],
        "cart_preview_has_more": len(plans) > 4,
    }

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
