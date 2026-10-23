import uuid
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from accounts.forms import AccountPasswordChangeForm, AccountProfileForm
from billing.models import PaymentOrder
from billing.services import OrderCreationError, create_payment_order
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


