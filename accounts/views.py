import hashlib
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.cache import cache
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from .forms import AccountPasswordChangeForm, AccountProfileForm, RegisterForm, VerificationResendForm
from .models import Customer

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    form = AccountProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        previous_email = request.user.email
        customer = form.save(commit=False)
        email_changed = customer.email.casefold() != previous_email.casefold()
        if email_changed:
            customer.is_active = False
        customer.save()
        if email_changed:
            try:
                _send_verification_email(request, customer)
            except Exception:
                logger.exception("Could not send email-change verification for customer %s", customer.pk)
            logout(request)
            return render(request, "accounts/verification_sent.html", {"email": customer.email})
        messages.success(request, "Your account details have been updated.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def password_change(request):
    form = AccountPasswordChangeForm(user=request.user, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Your password has been changed.")
        return redirect("accounts:profile")
    return render(request, "accounts/password_change.html", {"form": form})


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("portal:dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        customer = form.save(commit=False)
        customer.is_active = False
        customer.save()
        try:
            _send_verification_email(request, customer)
        except Exception:
            logger.exception("Could not send verification email for newly registered customer %s", customer.pk)
        return render(request, "accounts/verification_sent.html", {"email": customer.email})
    return render(request, "portal/register.html", {"form": form})


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Verification tokens become invalid after account activation."""

    def _make_hash_value(self, user, timestamp):
        return f"{super()._make_hash_value(user, timestamp)}:{user.is_active}"


email_verification_token = EmailVerificationTokenGenerator()


def _verification_throttle_key(email, ip):
    raw = f"{email.strip().casefold()}|{ip or 'unknown'}".encode("utf-8")
    return "account-verification-email:" + hashlib.sha256(raw).hexdigest()


def _send_verification_email(request, customer):
    key = _verification_throttle_key(customer.email, request.META.get("REMOTE_ADDR", ""))
    cache.add(key, 0, timeout=60 * 60)
    try:
        sent_count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=60 * 60)
        sent_count = 1
    if sent_count > 5:
        return False

    uid = urlsafe_base64_encode(force_bytes(customer.pk))
    token = email_verification_token.make_token(customer)
    verify_url = request.build_absolute_uri(
        reverse("accounts:verify_email", kwargs={"uidb64": uid, "token": token})
    )
    context = {"user": customer, "verify_url": verify_url, "valid_hours": 24}
    body = render_to_string("registration/email_verification_email.txt", context)
    html_body = render_to_string("registration/email_verification_email.html", context)
    send_mail(
        subject="Verify your Nebula Vault email",
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[customer.email],
        html_message=html_body,
        fail_silently=False,
    )
    return True


@require_http_methods(["GET", "POST"])
def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        customer = Customer.objects.get(pk=uid)
    except Exception:
        customer = None

    if customer is not None and not customer.is_active and email_verification_token.check_token(customer, token):
        customer.is_active = True
        customer.save(update_fields=["is_active"])
        messages.success(request, "Your email has been verified. You can now sign in.")
        return redirect("login")

    if customer is not None and customer.is_active:
        return render(request, "accounts/verification_result.html", {"already_verified": True, "success": True})
    return render(request, "accounts/verification_result.html", {"already_verified": False, "success": False}, status=400)


@require_http_methods(["GET", "POST"])
def resend_verification(request):
    if request.user.is_authenticated:
        return redirect("portal:dashboard")
    form = VerificationResendForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip()
        customer = Customer.objects.filter(email__iexact=email, is_active=False).first()
        if customer:
            try:
                _send_verification_email(request, customer)
            except Exception:
                # Avoid disclosing account existence or SMTP delivery details.
                logger.exception("Could not send requested account verification email")
        return render(request, "accounts/verification_resend_done.html")
    return render(request, "accounts/verification_resend.html", {"form": form})
