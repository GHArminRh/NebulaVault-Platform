from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def money(minor_units):
    """Format an integer amount stored in the currency's minor unit."""
    try:
        return f"{(Decimal(minor_units) / Decimal(100)):,.2f}"
    except (TypeError, ValueError, ArithmeticError):
        return "—"
