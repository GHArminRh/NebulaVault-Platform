import uuid
from collections import defaultdict

from django.conf import settings
from django.db import transaction
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from accounts.forms import AccountPasswordChangeForm, AccountProfileForm
from billing.models import PaymentAttempt, PaymentOrder
from billing.services import (
    OrderCreationError,
    PaymentAttemptCreationError,
    PaymentFinalizationError,
    create_payment_attempt,
    create_payment_order,
    finalize_payment,
)
from catalog.models import Plan, Product, Release
from subscriptions.models import Subscription
from subscriptions.services import TrialAlreadyUsed, TrialUnavailable, start_trial

def home(request):
    products = Product.objects.filter(is_active=True).prefetch_related(Prefetch("plans", queryset=Plan.objects.filter(is_active=True)))[:3]
    releases = Release.objects.filter(is_published=True, product__is_active=True).select_related("product")[:3]
    return render(request, "portal/home.html", {"products": products, "releases": releases})

def products(request):
    items = Product.objects.filter(is_active=True).prefetch_related(Prefetch("plans", queryset=Plan.objects.filter(is_active=True)))
    return render(request, "portal/products.html", {"products": items})

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    plans = product.plans.filter(is_active=True)
    releases = product.releases.filter(is_published=True)
    has_used_trial = request.user.is_authenticated and product.trial_redemptions.filter(user=request.user).exists()
    return render(request, "portal/product_detail.html", {"product": product, "plans": plans, "releases": releases, "has_used_trial": has_used_trial})

def pricing(request):
    plans = Plan.objects.filter(is_active=True, product__is_active=True).select_related("product")
    return render(request, "portal/pricing.html", {"plans": plans})

@login_required
def dashboard(request):
    profile_form = AccountProfileForm(instance=request.user)
    password_form = AccountPasswordChangeForm(user=request.user)

    if request.method == "POST":
        action = request.POST.get("account_action")
        if action == "profile":
            profile_form = AccountProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "اطلاعات حساب شما با موفقیت ذخیره شد.")
                return redirect("portal:dashboard")
        elif action == "password":
            password_form = AccountPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                customer = password_form.save()
                update_session_auth_hash(request, customer)
                messages.success(request, "رمز عبور شما با موفقیت تغییر کرد.")
                return redirect("portal:dashboard")
        else:
            messages.error(request, "درخواست نامعتبر است. دوباره تلاش کنید.")

    all_subscriptions = list(Subscription.objects.filter(user=request.user).select_related("product", "plan"))
    orders = PaymentOrder.objects.filter(user=request.user).select_related("plan", "plan__product")
    return render(request, "portal/dashboard.html", {
        "subscriptions": all_subscriptions[:5], "orders": orders[:5],
        "active_count": sum(1 for item in all_subscriptions if item.is_currently_valid),
        "pending_count": orders.filter(status=PaymentOrder.Status.PENDING).count(),
        "now": timezone.now(),
        "profile_form": profile_form,
        "password_form": password_form,
    })

@login_required
def subscriptions(request):
    items = Subscription.objects.filter(user=request.user).select_related("product", "plan")
    return render(request, "portal/subscriptions.html", {"subscriptions": items})

@login_required
def orders(request):
    items = PaymentOrder.objects.filter(user=request.user).select_related("plan", "plan__product", "subscription")
    return render(request, "portal/orders.html", {"orders": items})

@login_required
def create_order(request, plan_id):
    if request.method != "POST":
        return redirect("portal:pricing")
    plan = get_object_or_404(Plan, pk=plan_id, is_active=True, product__is_active=True)
    try:
        order = create_payment_order(user=request.user, plan_id=plan.pk,
            idempotency_key=request.POST.get("idempotency_key") or uuid.uuid4(),
            subscription_id=request.POST.get("subscription_id") or None)
    except OrderCreationError as exc:
        messages.error(request, str(exc))
        return redirect("portal:product_detail", slug=plan.product.slug)
    messages.success(request, f"Order {order.order_number} was created. Payment processing is not connected yet.")
    return redirect("portal:orders")

def _cart_plan_ids(request):
    """Return unique, stringified plan UUIDs stored in the user's session."""
    raw_ids = request.session.get("nebula_cart", [])
    if not isinstance(raw_ids, list):
        return []
    return list(dict.fromkeys(str(value) for value in raw_ids if value))


def cart_add(request, plan_id):
    if request.method != "POST":
        return redirect("portal:pricing")

    plan = get_object_or_404(
        Plan.objects.select_related("product"),
        pk=plan_id,
        is_active=True,
        product__is_active=True,
    )
    plan_ids = _cart_plan_ids(request)
    if str(plan.pk) not in plan_ids:
        plan_ids.append(str(plan.pk))
        request.session["nebula_cart"] = plan_ids
        messages.success(request, f"{plan.name} was added to your cart.")
    else:
        messages.info(request, f"{plan.name} is already in your cart.")
    return redirect(request.POST.get("next") or "portal:cart")


def cart(request):
    plan_ids = _cart_plan_ids(request)
    plans = list(
        Plan.objects.filter(
            pk__in=plan_ids,
            is_active=True,
            product__is_active=True,
        ).select_related("product")
    )
    valid_ids = {str(plan.pk) for plan in plans}
    if valid_ids != set(plan_ids):
        request.session["nebula_cart"] = [
            plan_id for plan_id in plan_ids if plan_id in valid_ids
        ]

    totals = defaultdict(int)
    for plan in plans:
        totals[plan.currency] += plan.price_minor_units
    currency_totals = [
        {"currency": currency, "amount_minor_units": amount}
        for currency, amount in sorted(totals.items())
    ]
    return render(request, "portal/cart.html", {
        "cart_plans": plans,
        "cart_totals": currency_totals,
        "cart_count": len(plans),
        "mock_payments_enabled": getattr(settings, "NEBULA_MOCK_PAYMENTS", settings.DEBUG),
    })


def cart_remove(request, plan_id):
    if request.method != "POST":
        return redirect("portal:cart")
    request.session["nebula_cart"] = [
        value for value in _cart_plan_ids(request) if value != str(plan_id)
    ]
    messages.success(request, "The item was removed from your cart.")
    return redirect("portal:cart")


def cart_clear(request):
    if request.method != "POST":
        return redirect("portal:cart")
    request.session["nebula_cart"] = []
    messages.success(request, "Your cart has been cleared.")
    return redirect("portal:cart")


@login_required
def checkout(request):
    if request.method != "POST":
        return redirect("portal:cart")

    if not getattr(settings, "NEBULA_MOCK_PAYMENTS", settings.DEBUG):
        messages.error(request, "Demo checkout is disabled. Please try again when payment processing is available.")
        return redirect("portal:cart")

    plan_ids = _cart_plan_ids(request)
    if not plan_ids:
        messages.info(request, "Your cart is empty.")
        return redirect("portal:cart")

    plans = list(
        Plan.objects.filter(
            pk__in=plan_ids,
            is_active=True,
            product__is_active=True,
        ).select_related("product")
    )
    if len(plans) != len(plan_ids):
        messages.error(request, "One or more items are no longer available. Please review your cart.")
        request.session["nebula_cart"] = [str(plan.pk) for plan in plans]
        return redirect("portal:cart")

    completed_orders = []
    try:
        # Keep the mock checkout all-or-nothing: a failure must not leave
        # only part of a multi-item cart marked as paid.
        with transaction.atomic():
            for plan in plans:
                order = (
                    PaymentOrder.objects
                    .filter(
                        user=request.user,
                        plan=plan,
                        status=PaymentOrder.Status.PENDING,
                    )
                    .order_by("-created_at")
                    .first()
                )
                if order is None:
                    order = create_payment_order(
                        user=request.user,
                        plan_id=plan.pk,
                        idempotency_key=uuid.uuid4(),
                    )

                if order.status == PaymentOrder.Status.PAID:
                    completed_orders.append(order)
                    continue

                attempt = create_payment_attempt(
                    user=request.user,
                    order_id=order.pk,
                    provider="mock",
                    idempotency_key=uuid.uuid4(),
                )
                finalize_payment(
                    attempt_id=attempt.pk,
                    provider_reference=f"mock-{order.order_number}",
                    confirmed_amount_minor_units=order.amount_minor_units,
                    confirmed_currency=order.currency,
                )
                completed_orders.append(order)
    except (OrderCreationError, PaymentAttemptCreationError, PaymentFinalizationError) as exc:
        messages.error(request, f"Checkout could not be completed: {exc}")
        return redirect("portal:cart")

    request.session["nebula_cart"] = []
    messages.success(
        request,
        f"Demo payment successful. {len(completed_orders)} order(s) completed and your access has been activated.",
    )
    return redirect("portal:orders")


@login_required
def start_trial(request, slug):
    if request.method != "POST":
        return redirect("portal:product_detail", slug=slug)
    product = get_object_or_404(Product, slug=slug, is_active=True)
    try:
        start_trial(user=request.user, product=product)
    except (TrialAlreadyUsed, TrialUnavailable) as exc:
        messages.error(request, str(exc))
        return redirect("portal:product_detail", slug=slug)
    messages.success(request, f"Your 7-day trial for {product.name} is ready.")
    return redirect("portal:subscriptions")


