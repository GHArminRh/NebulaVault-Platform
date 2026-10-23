from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from .forms import AccountPasswordChangeForm, AccountProfileForm, RegisterForm


@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    form = AccountProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your account details have been updated.")
        return redirect("customer_accounts:profile")
    return render(request, "accounts/profile.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def password_change(request):
    form = AccountPasswordChangeForm(user=request.user, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Your password has been changed.")
        return redirect("customer_accounts:profile")
    return render(request, "accounts/password_change.html", {"form": form})


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("portal:dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        customer = form.save()
        login(request, customer, backend="customer_accounts.backends.CustomerAuthenticationBackend")
        messages.success(request, "Your account has been created.")
        return redirect("portal:dashboard")
    return render(request, "portal/register.html", {"form": form})
