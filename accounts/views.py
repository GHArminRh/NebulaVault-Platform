import hashlib
import logging
import secrets
import hmac
from datetime import timedelta

from django.utils import timezone
from django.utils.crypto import salted_hmac

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
from .forms import AccountPasswordChangeForm, AccountPasswordResetForm, AccountProfileForm, AccountSetPasswordForm, RegisterForm, VerificationResendForm
from .models import AccountEmailLog, Customer

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
                sent = _send_verification_email(request, customer)
                if sent:
                    messages.info(request, "A verification email has been sent. Enter the six-digit code below or use the link in the email.")
                else:
                    messages.warning(request, "The verification email limit has been reached. Please try again later.")
            except Exception:
                logger.exception("Could not send email-change verification for customer %s", customer.pk)
                messages.error(request, "We couldn’t send the verification email right now. Please try again later.")
            logout(request)
            return render(request, "accounts/email_code_form.html", {"purpose": "verification", "email": customer.email})
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
            sent = _send_verification_email(request, customer)
            if sent:
                messages.info(request, "A verification email has been sent. Enter the six-digit code below or use the link in the email.")
            else:
                messages.warning(request, "The verification email limit has been reached. Please try again later.")
        except Exception:
            logger.exception("Could not send verification email for newly registered customer %s", customer.pk)
            messages.error(request, "We couldn’t send the verification email right now. You can request another one below.")
        return render(request, "accounts/email_code_form.html", {"purpose": "verification", "email": customer.email})
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
    code = _new_email_code()
    _supersede_codes(customer, AccountEmailLog.Purpose.VERIFICATION)
    log = AccountEmailLog.objects.create(
        customer=customer, recipient=customer.email, purpose=AccountEmailLog.Purpose.VERIFICATION,
        status=AccountEmailLog.Status.FAILED, expires_at=timezone.now() + timedelta(hours=24),
        ip_address=request.META.get("REMOTE_ADDR") or None, code_hash=_code_digest(code),
    )
    context = {"user": customer, "verify_url": verify_url, "valid_hours": 24, "verification_code": code}
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
    log.status = AccountEmailLog.Status.SENT
    log.sent_at = timezone.now()
    log.error_message = ""
    log.save(update_fields=["status", "sent_at", "error_message"])
    cache.set(
        _verification_resend_cooldown_key(customer.email, request.META.get("REMOTE_ADDR", "")),
        1,
        timeout=30,
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


def _verification_resend_cooldown_key(email, ip):
    raw = f"{email.strip().casefold()}|{ip or 'unknown'}".encode("utf-8")
    return "account-verification-resend-cooldown:" + hashlib.sha256(raw).hexdigest()


@require_http_methods(["GET", "POST"])
def resend_verification(request):
    if request.user.is_authenticated:
        return redirect("portal:dashboard")
    form = VerificationResendForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip()
        ip = request.META.get("REMOTE_ADDR", "")
        cooldown_key = _verification_resend_cooldown_key(email, ip)
        if not cache.add(cooldown_key, 1, timeout=30):
            messages.warning(request, "Please wait 30 seconds before requesting another verification email.")
            return render(request, "accounts/email_code_form.html", {
                "purpose": "verification", "email": email, "resend_cooldown": True,
            })
        customer = Customer.objects.filter(email__iexact=email, is_active=False).first()
        if customer:
            try:
                sent = _send_verification_email(request, customer)
                if sent:
                    messages.success(request, "If this account is awaiting verification, a new email has been sent.")
                else:
                    messages.warning(request, "The email request limit has been reached. Please try again later.")
            except Exception:
                # Avoid disclosing account existence or SMTP delivery details.
                logger.exception("Could not send requested account verification email")
                messages.error(request, "We couldn’t send the email right now. Please try again later.")
        else:
            messages.success(request, "If this account is awaiting verification, a new email has been sent.")
        return render(request, "accounts/email_code_form.html", {
            "purpose": "verification", "email": email, "resend_cooldown": True,
        })
    return render(request, "accounts/verification_resend.html", {"form": form})


def _new_email_code():
    return f"{secrets.randbelow(1_000_000):06d}"


def _code_digest(code):
    return salted_hmac("accounts.email_code", str(code), algorithm="sha256").hexdigest()


def _supersede_codes(customer, purpose):
    AccountEmailLog.objects.filter(
        customer=customer, purpose=purpose, status=AccountEmailLog.Status.SENT,
        consumed_at__isnull=True,
    ).update(status=AccountEmailLog.Status.SUPERSEDED)


def _record_failed_email(customer, purpose, recipient, request, exc):
    AccountEmailLog.objects.create(
        customer=customer, recipient=recipient, purpose=purpose,
        status=AccountEmailLog.Status.FAILED,
        ip_address=request.META.get("REMOTE_ADDR") or None,
        error_message=str(exc)[:1000],
    )


@require_http_methods(["GET", "POST"])
def verify_email_code(request):
    if request.user.is_authenticated:
        return redirect("portal:dashboard")
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        code = request.POST.get("code", "").strip()
        customer = Customer.objects.filter(email__iexact=email, is_active=False).first()
        entry = None
        if customer and len(code) == 6 and code.isdigit():
            entry = AccountEmailLog.objects.filter(
                customer=customer, purpose=AccountEmailLog.Purpose.VERIFICATION,
                status=AccountEmailLog.Status.SENT, consumed_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).order_by("-created_at").first()
        if entry and entry.failed_attempts < 5 and hmac.compare_digest(entry.code_hash, _code_digest(code)):
            entry.status = AccountEmailLog.Status.USED
            entry.consumed_at = timezone.now()
            entry.save(update_fields=["status", "consumed_at"])
            customer.is_active = True
            customer.save(update_fields=["is_active"])
            messages.success(request, "Your email has been verified. You can now sign in.")
            return redirect("login")
        if entry:
            entry.failed_attempts += 1
            if entry.failed_attempts >= 5:
                entry.status = AccountEmailLog.Status.EXPIRED
            entry.save(update_fields=["failed_attempts", "status"])
        return render(request, "accounts/email_code_form.html", {
            "purpose": "verification", "email": email,
            "error": "The code is invalid, expired, or has reached its attempt limit.",
        }, status=400)
    return render(request, "accounts/email_code_form.html", {"purpose": "verification"})


@require_http_methods(["GET", "POST"])
def password_reset_request(request):
    if request.user.is_authenticated:
        return redirect("portal:dashboard")
    form = AccountPasswordResetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip()
        throttle_key = "account-password-reset:" + hashlib.sha256(f"{email.casefold()}|{request.META.get('REMOTE_ADDR', '')}".encode()).hexdigest()
        cache.add(throttle_key, 0, timeout=3600)
        try:
            requests_this_hour = cache.incr(throttle_key)
        except ValueError:
            cache.set(throttle_key, 1, timeout=3600)
            requests_this_hour = 1
        if requests_this_hour <= 5:
            customer = Customer.objects.filter(email__iexact=email, is_active=True).first()
            if customer and customer.has_usable_password():
                code = _new_email_code()
                _supersede_codes(customer, AccountEmailLog.Purpose.PASSWORD_RESET)
                log = AccountEmailLog.objects.create(
                    customer=customer, recipient=customer.email, purpose=AccountEmailLog.Purpose.PASSWORD_RESET,
                    status=AccountEmailLog.Status.FAILED, expires_at=timezone.now() + timedelta(minutes=15),
                    ip_address=request.META.get("REMOTE_ADDR") or None, code_hash=_code_digest(code),
                )
                uid = urlsafe_base64_encode(force_bytes(customer.pk))
                token = PasswordResetTokenGenerator().make_token(customer)
                reset_url = request.build_absolute_uri(reverse(
                    "accounts:password_reset_confirm", kwargs={"uidb64": uid, "token": token}
                ))
                context = {"user": customer, "email": customer.email, "reset_url": reset_url,
                           "protocol": request.scheme, "domain": request.get_host(),
                           "password_reset_code": code, "valid_minutes": 15}
                try:
                    send_mail(
                        "Reset your Nebula Vault password",
                        render_to_string("registration/password_reset_email.txt", context),
                        settings.DEFAULT_FROM_EMAIL, [customer.email],
                        html_message=render_to_string("registration/password_reset_email.html", context),
                        fail_silently=False,
                    )
                    log.status = AccountEmailLog.Status.SENT
                    log.sent_at = timezone.now()
                    log.save(update_fields=["status", "sent_at"])
                except Exception as exc:
                    log.error_message = str(exc)[:1000]
                    log.save(update_fields=["error_message"])
                    logger.exception("Could not send password recovery email for customer %s", customer.pk)
        return redirect("accounts:password_reset_done")
    return render(request, "accounts/password_reset_form.html", {"form": form})


@require_http_methods(["GET", "POST"])
def password_reset_code(request):
    if request.user.is_authenticated:
        return redirect("portal:dashboard")
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        code = request.POST.get("code", "").strip()
        customer = Customer.objects.filter(email__iexact=email, is_active=True).first()
        entry = None
        if customer and len(code) == 6 and code.isdigit():
            entry = AccountEmailLog.objects.filter(
                customer=customer, purpose=AccountEmailLog.Purpose.PASSWORD_RESET,
                status=AccountEmailLog.Status.SENT, consumed_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).order_by("-created_at").first()
        if entry and entry.failed_attempts < 5 and hmac.compare_digest(entry.code_hash, _code_digest(code)):
            entry.status = AccountEmailLog.Status.USED
            entry.consumed_at = timezone.now()
            entry.save(update_fields=["status", "consumed_at"])
            uid = urlsafe_base64_encode(force_bytes(customer.pk))
            token = PasswordResetTokenGenerator().make_token(customer)
            return redirect("accounts:password_reset_confirm", uidb64=uid, token=token)
        if entry:
            entry.failed_attempts += 1
            if entry.failed_attempts >= 5:
                entry.status = AccountEmailLog.Status.EXPIRED
            entry.save(update_fields=["failed_attempts", "status"])
        return render(request, "accounts/email_code_form.html", {
            "purpose": "password_reset", "email": email,
            "error": "The code is invalid, expired, or has reached its attempt limit.",
        }, status=400)
    return render(request, "accounts/email_code_form.html", {"purpose": "password_reset"})




@require_http_methods(["GET", "POST"])
def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        customer = Customer.objects.get(pk=uid, is_active=True)
    except (TypeError, ValueError, OverflowError, Customer.DoesNotExist):
        customer = None

    token_generator = PasswordResetTokenGenerator()
    validlink = bool(customer and token_generator.check_token(customer, token))
    form = AccountSetPasswordForm(customer, request.POST or None) if validlink else None
    if request.method == "POST" and validlink and form and form.is_valid():
        form.save()
        messages.success(request, "Your password has been reset. You can now sign in.")
        return redirect("accounts:password_reset_complete")
    return render(request, "accounts/password_reset_confirm.html", {
        "form": form, "validlink": validlink, "title": "Set a new password",
    }, status=200 if validlink else 400)
