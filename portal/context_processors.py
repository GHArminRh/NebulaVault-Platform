from collections import defaultdict

from django.db import DatabaseError

from catalog.models import Plan


def cart_context(request):
    """Expose cart data site-wide without breaking error pages if the DB is unavailable."""
    raw_ids = request.session.get("nebula_cart", [])
    if not isinstance(raw_ids, list):
        plan_ids = []
    else:
        plan_ids = list(dict.fromkeys(str(value) for value in raw_ids if value))

    plans = []
    dashboard_licenses = ()
    try:
        if plan_ids:
            plans = list(
                Plan.objects.filter(
                    pk__in=plan_ids,
                    is_active=True,
                    product__is_active=True,
                ).select_related("product")
            )
        if (
            getattr(request, "user", None)
            and request.user.is_authenticated
            and request.path.rstrip("/").endswith("/dashboard")
        ):
            from licensing.models import License

            dashboard_licenses = (
                License.objects.filter(subscription__user=request.user)
                .select_related("subscription", "subscription__product", "subscription__plan")
                .order_by("-created_at")
            )
    except DatabaseError:
        # Error templates extend the public base layout. If the database itself
        # caused a 500, keep the shared layout renderable without cart/license data.
        plans = []
        dashboard_licenses = ()

    totals = defaultdict(int)
    for plan in plans:
        totals[plan.currency] += plan.price_minor_units

    return {
        "cart_count": len(plans),
        "cart_preview_plans": plans[:4],
        "cart_preview_totals": [
            {"currency": currency, "amount_minor_units": amount}
            for currency, amount in sorted(totals.items())
        ],
        "cart_preview_has_more": len(plans) > 4,
        "dashboard_licenses": dashboard_licenses,
    }
