def cart_context(request):
    """Expose a lightweight cart count to the global site header."""
    raw_ids = request.session.get("nebula_cart", [])
    if not isinstance(raw_ids, list):
        return {"cart_count": 0}
    return {"cart_count": len({str(value) for value in raw_ids if value})}
