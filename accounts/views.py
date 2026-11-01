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
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from .forms import AccountPasswordChangeForm, AccountPasswordResetForm, AccountProfileForm, AccountSetPasswordForm, RegisterForm, StaffAccountProfileForm, VerificationResendForm
from .models import AccountEmailLog, Customer
from .two_factor import consume_recovery_code, decrypt_totp_secret, encrypt_totp_secret, new_totp_secret, provisioning_uri, qr_data_uri, send_email_code, store_recovery_codes, verify_email_challenge, verify_totp

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    # ModelForm validation mutates its instance in memory. Capture the persisted
    # value before binding/validating the form so email changes are detected.
    previous_email = request.user.email
    form = AccountProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        customer = form.save(commit=False)
        email_changed = customer.email.casefold() != previous_email.casefold()
        if email_changed:
            customer.is_active = False
        customer.save()
        if email_changed:
            try:
                sent = _send_verification_email(request, customer)
                if sent:
                    messages.info(request, "ایمیل تأیید برای شما ارسال شد. کد شش‌رقمی زیر را وارد کنید یا از پیوند داخل ایمیل استفاده کنید.")
                else:
                    messages.warning(request, "به سقف مجاز ارسال ایمیل تأیید رسیده‌اید. لطفاً بعداً دوباره تلاش کنید.")
            except Exception:
                logger.exception("Could not send email-change verification for customer %s", customer.pk)
                messages.error(request, "در حال حاضر ارسال ایمیل تأیید ممکن نشد. لطفاً بعداً دوباره تلاش کنید.")
            logout(request)
            return render(request, "accounts/email_code_form.html", {"purpose": "verification", "email": customer.email})
        messages.success(request, "اطلاعات حساب شما به‌روزرسانی شد.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def password_change(request):
    form = AccountPasswordChangeForm(user=request.user, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "رمز عبور شما تغییر کرد.")
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
                messages.info(request, "ایمیل تأیید برای شما ارسال شد. کد شش‌رقمی زیر را وارد کنید یا از پیوند داخل ایمیل استفاده کنید.")
            else:
                messages.warning(request, "به سقف مجاز ارسال ایمیل تأیید رسیده‌اید. لطفاً بعداً دوباره تلاش کنید.")
        except Exception:
            logger.exception("Could not send verification email for newly registered customer %s", customer.pk)
            messages.error(request, "در حال حاضر ارسال ایمیل تأیید ممکن نشد. می‌توانید از گزینه زیر دوباره درخواست دهید.")
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
    try:
        body = render_to_string("registration/email_verification_email.txt", context)
        html_body = render_to_string("registration/email_verification_email.html", context)
        send_mail(
            subject="تأیید نشانی ایمیل نبیولا والت",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer.email],
            html_message=html_body,
            fail_silently=False,
        )
    except Exception as exc:
        log.status = AccountEmailLog.Status.FAILED
        log.error_message = str(exc)[:1000]
        log.save(update_fields=["status", "error_message"])
        raise

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

    if customer is not None and not customer.is_banned and not customer.is_active and email_verification_token.check_token(customer, token):
        customer.is_active = True
        customer.save(update_fields=["is_active"])
        login(request, customer, backend="accounts.backends.CustomerAuthenticationBackend")
        messages.success(request, "نشانی ایمیل شما با موفقیت تأیید شد. خوش آمدید!")
        return redirect("portal:dashboard")

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
            messages.warning(request, "برای درخواست ایمیل تأیید بعدی، ۳۰ ثانیه صبر کنید.")
            return render(request, "accounts/email_code_form.html", {
                "purpose": "verification", "email": email, "resend_cooldown": True,
            })
        customer = Customer.objects.filter(email__iexact=email, is_active=False, is_banned=False).first()
        if customer:
            try:
                sent = _send_verification_email(request, customer)
                if sent:
                    messages.success(request, "اگر حسابی با این نشانی در انتظار تأیید باشد، ایمیل جدیدی ارسال شده است.")
                else:
                    messages.warning(request, "به سقف مجاز درخواست ایمیل رسیده‌اید. لطفاً بعداً دوباره تلاش کنید.")
            except Exception:
                # Avoid disclosing account existence or SMTP delivery details.
                logger.exception("Could not send requested account verification email")
                messages.error(request, "در حال حاضر ارسال ایمیل ممکن نشد. لطفاً بعداً دوباره تلاش کنید.")
        else:
            messages.success(request, "اگر حسابی با این نشانی در انتظار تأیید باشد، ایمیل جدیدی ارسال شده است.")
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
        customer = Customer.objects.filter(email__iexact=email, is_active=False, is_banned=False).first()
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
            login(request, customer, backend="accounts.backends.CustomerAuthenticationBackend")
            messages.success(request, "نشانی ایمیل شما با موفقیت تأیید شد. خوش آمدید!")
            return redirect("portal:dashboard")
        if entry:
            entry.failed_attempts += 1
            if entry.failed_attempts >= 5:
                entry.status = AccountEmailLog.Status.EXPIRED
            entry.save(update_fields=["failed_attempts", "status"])
        return render(request, "accounts/email_code_form.html", {
            "purpose": "verification", "email": email,
            "error": "کد واردشده نامعتبر است، منقضی شده یا تعداد تلاش‌های مجاز به پایان رسیده است.",
        }, status=400)
    return render(request, "accounts/email_code_form.html", {"purpose": "verification"})


def _password_reset_resend_cooldown_key(email, ip):
    raw = f"{email.strip().casefold()}|{ip or 'unknown'}".encode("utf-8")
    return "account-password-reset-resend-cooldown:" + hashlib.sha256(raw).hexdigest()


@require_http_methods(["GET", "POST"])
def password_reset_request(request):
    if request.user.is_authenticated:
        return redirect("portal:dashboard")
    form = AccountPasswordResetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip()
        ip = request.META.get("REMOTE_ADDR", "")
        cooldown_key = _password_reset_resend_cooldown_key(email, ip)
        if not cache.add(cooldown_key, 1, timeout=30):
            messages.warning(request, "برای درخواست ایمیل بازیابی بعدی، ۳۰ ثانیه صبر کنید.")
            return render(request, "accounts/email_code_form.html", {
                "purpose": "password_reset", "email": email, "resend_cooldown": True,
            })
        throttle_key = "account-password-reset:" + hashlib.sha256(f"{email.casefold()}|{ip}".encode()).hexdigest()
        cache.add(throttle_key, 0, timeout=3600)
        try:
            requests_this_hour = cache.incr(throttle_key)
        except ValueError:
            cache.set(throttle_key, 1, timeout=3600)
            requests_this_hour = 1
        if requests_this_hour <= 5:
            customer = Customer.objects.filter(email__iexact=email, is_active=True, is_banned=False).first()
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
                        "بازیابی رمز عبور نبیولا والت",
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
        messages.info(request, "اگر حساب واجد شرایطی با این نشانی وجود داشته باشد، پیام بازیابی ارسال شده است. کد شش‌رقمی را وارد کنید یا از پیوند داخل ایمیل استفاده کنید.")
        return render(request, "accounts/email_code_form.html", {
            "purpose": "password_reset", "email": email,
        })
    return render(request, "accounts/password_reset_form.html", {"form": form})


@require_http_methods(["GET", "POST"])
def password_reset_code(request):
    if request.user.is_authenticated:
        return redirect("portal:dashboard")
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        code = request.POST.get("code", "").strip()
        customer = Customer.objects.filter(email__iexact=email, is_active=True, is_banned=False).first()
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
            "error": "کد واردشده نامعتبر است، منقضی شده یا تعداد تلاش‌های مجاز به پایان رسیده است.",
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
        messages.success(request, "رمز عبور شما بازنشانی شد. اکنون می‌توانید وارد شوید.")
        return redirect("accounts:password_reset_complete")
    return render(request, "accounts/password_reset_confirm.html", {
        "form": form, "validlink": validlink, "title": "تنظیم رمز عبور جدید",
    }, status=200 if validlink else 400)




def _two_factor_session_key(user):
    return f"nv_totp_enrollment:{user._meta.label_lower}:{user.pk}"


def _has_two_factor(user):
    return bool(user.two_factor_enabled or user.email_two_factor_enabled)


def _verify_user_second_factor(user, data, purpose="setup"):
    valid = False
    if user.two_factor_enabled and verify_totp(
        decrypt_totp_secret(user.two_factor_secret), data.get("otp_token")
    ):
        valid = True
    if not valid and user.email_two_factor_enabled and verify_email_challenge(
        user, data.get("email_otp_token"), purpose=purpose
    ):
        valid = True
    if not valid and consume_recovery_code(user, data.get("recovery_code")):
        valid = True
    return valid


def _revoke_customer_api_tokens(user):
    if isinstance(user, Customer):
        from api.models import CustomerAPIToken
        CustomerAPIToken.objects.filter(
            customer=user, revoked_at__isnull=True
        ).update(revoked_at=timezone.now())


def _process_two_factor_post(request, user):
    action = request.POST.get("security_action")
    password = request.POST.get("current_password", "")
    if action == "request_email_setup_code":
        if not user.check_password(password):
            messages.error(request, "رمز عبور فعلی نادرست است.")
            return
        try:
            sent = send_email_code(request, user, purpose="setup")
        except Exception:
            messages.error(request, "ارسال کد ایمیل ممکن نشد. لطفاً بعداً دوباره تلاش کنید.")
            return
        if sent:
            messages.success(request, "کد تأیید به ایمیل حساب شما ارسال شد و ۱۰ دقیقه اعتبار دارد.")
        else:
            messages.warning(request, "برای ارسال کد جدید، حداقل ۶۰ ثانیه صبر کنید.")
        return

    if action == "enable_two_factor":
        secret = request.session.get(_two_factor_session_key(user), "")
        if user.check_password(password) and secret and verify_totp(secret, request.POST.get("otp_token")):
            user.two_factor_secret = encrypt_totp_secret(secret)
            user.two_factor_enabled = True
            user.save(update_fields=["two_factor_secret", "two_factor_enabled"])
            _revoke_customer_api_tokens(user)
            if not user.recovery_codes:
                request.session["nv_new_recovery_codes"] = store_recovery_codes(user)
            request.session.pop(_two_factor_session_key(user), None)
            messages.success(request, "تأیید با برنامه احراز هویت فعال شد.")
        else:
            messages.error(request, "رمز عبور یا کد برنامه احراز هویت معتبر نیست؛ دوباره تلاش کنید.")
    elif action == "enable_email_two_factor":
        if (
            user.check_password(password)
            and verify_email_challenge(user, request.POST.get("email_otp_token"), purpose="setup")
        ):
            user.email_two_factor_enabled = True
            user.save(update_fields=["email_two_factor_enabled"])
            _revoke_customer_api_tokens(user)
            if not user.recovery_codes:
                request.session["nv_new_recovery_codes"] = store_recovery_codes(user)
            messages.success(request, "تأیید دومرحله‌ای ایمیلی فعال شد.")
        else:
            messages.error(request, "رمز عبور یا کد ایمیل معتبر نیست، منقضی شده یا قبلاً استفاده شده است.")
    elif action in {"disable_two_factor", "disable_email_two_factor"}:
        if not user.check_password(password) or not _verify_user_second_factor(user, request.POST, purpose="setup"):
            messages.error(request, "رمز عبور یا کد تأیید معتبر نیست؛ تنظیمات امنیتی تغییری نکرد.")
            return
        if action == "disable_two_factor":
            user.two_factor_enabled = False
            user.two_factor_secret = ""
            fields = ["two_factor_enabled", "two_factor_secret"]
            message = "تأیید با برنامه احراز هویت غیرفعال شد."
        else:
            user.email_two_factor_enabled = False
            fields = ["email_two_factor_enabled"]
            message = "تأیید دومرحله‌ای ایمیلی غیرفعال شد."
        if not _has_two_factor(user):
            user.recovery_codes = []
            fields.append("recovery_codes")
        user.save(update_fields=fields)
        messages.success(request, message)
    elif action == "regenerate_recovery_codes":
        if user.check_password(password) and _has_two_factor(user) and _verify_user_second_factor(user, request.POST, purpose="setup"):
            request.session["nv_new_recovery_codes"] = store_recovery_codes(user)
            messages.success(request, "کدهای بازیابی جدید ساخته شدند؛ کدهای قبلی دیگر معتبر نیستند.")
        else:
            messages.error(request, "برای ساخت کدهای جدید، رمز عبور و یک روش تأیید معتبر لازم است.")
    else:
        messages.error(request, "درخواست نامعتبر است.")


def _two_factor_context(request, user):
    context = {
        "two_factor_enabled": user.two_factor_enabled,
        "email_two_factor_enabled": user.email_two_factor_enabled,
        "two_factor_active": _has_two_factor(user),
        "recovery_codes_remaining": len(user.recovery_codes or []),
        "new_recovery_codes": request.session.pop("nv_new_recovery_codes", []),
    }
    if not user.two_factor_enabled:
        key = _two_factor_session_key(user)
        secret = request.session.get(key)
        if not secret:
            secret = new_totp_secret()
            request.session[key] = secret
        uri = provisioning_uri(secret, user.get_username())
        context.update({
            "two_factor_secret": secret,
            "two_factor_qr": qr_data_uri(uri),
            "two_factor_uri": uri,
        })
    return context

@login_required
@require_http_methods(["GET", "POST"])
def customer_two_factor_settings(request):
    if getattr(request.user, "is_staff", False):
        return redirect("staff-account")
    if request.method == "POST":
        _process_two_factor_post(request, request.user)
        return redirect("accounts:two_factor_settings")
    return render(request, "accounts/two_factor_settings.html", _two_factor_context(request, request.user))


@staff_member_required
@require_http_methods(["GET", "POST"])
def staff_account(request):
    if request.method == "POST":
        action = request.POST.get("account_action")
        if action == "profile":
            form = StaffAccountProfileForm(request.POST, request.FILES, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, "Your profile was updated.")
                return redirect("staff-account")
            context = _two_factor_context(request, request.user)
            context["profile_form"] = form
            return render(request, "admin/staff_account.html", context)
        _process_two_factor_post(request, request.user)
        return redirect("staff-account")
    return render(request, "admin/staff_account.html", {
        **_two_factor_context(request, request.user),
        "profile_form": StaffAccountProfileForm(instance=request.user),
    })


class CustomerLoginView(LoginView):
    """Route account states accurately and throttle repeated failed login attempts."""

    LOGIN_FAILURE_LIMIT = 5
    LOGIN_FAILURE_WINDOW_SECONDS = 15 * 60

    def _login_attempt_key(self):
        # Cloudflare supplies the visitor IP in this header. The email is included
        # so a single visitor's typo does not throttle unrelated accounts.
        email = (self.request.POST.get("username") or "").strip().casefold()
        ip = (
            self.request.META.get("HTTP_CF_CONNECTING_IP")
            or self.request.META.get("REMOTE_ADDR", "")
            or "unknown"
        )
        digest = hashlib.sha256(f"{ip}|{email}".encode("utf-8")).hexdigest()
        return f"customer-login-failures:{digest}"

    def post(self, request, *args, **kwargs):
        key = self._login_attempt_key()
        if cache.get(key, 0) >= self.LOGIN_FAILURE_LIMIT:
            form = self.get_form()
            form.add_error(
                None,
                "به‌دلیل چند تلاش ناموفق، ورود این حساب موقتاً محدود شده است. لطفاً ۱۵ دقیقه دیگر دوباره تلاش کنید.",
            )
            return render(
                request,
                self.template_name,
                self.get_context_data(form=form, login_throttled=True),
                status=429,
            )
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        # A successful login clears the counter for this IP/account pair.
        cache.delete(self._login_attempt_key())
        return super().form_valid(form)

    def form_invalid(self, form):
        # Resolve the account state here as well as in the form. This keeps the
        # verification route reliable when AuthenticationForm rejects an inactive
        # customer before Django assigns form.get_user().
        email = (self.request.POST.get("username") or "").strip()
        password = self.request.POST.get("password") or ""
        human_check_passed = bool(form.cleaned_data.get("turnstile_verified"))

        customer = None
        if email and password and human_check_passed:
            candidate = Customer.objects.filter(email__iexact=email).first()
            if candidate and candidate.check_password(password):
                customer = candidate

        # Count only credential failures after a successful human check. CAPTCHA
        # failures, banned accounts with the correct password, and inactive
        # accounts with the correct password do not consume this counter.
        failure_count = None
        if human_check_passed and not (
            customer and password and customer.check_password(password)
        ):
            key = self._login_attempt_key()
            cache.add(key, 0, timeout=self.LOGIN_FAILURE_WINDOW_SECONDS)
            try:
                failure_count = cache.incr(key)
            except ValueError:
                cache.set(key, 1, timeout=self.LOGIN_FAILURE_WINDOW_SECONDS)
                failure_count = 1

        if customer and customer.is_banned:
            messages.error(self.request, "دسترسی حساب شما توسط مدیر مسدود شده است.")
            return render(
                self.request,
                self.template_name,
                self.get_context_data(form=form, banned_account=True),
                status=200,
            )

        inactive_email = (
            customer.email if customer and not customer.is_active
            else getattr(form, "inactive_email", None)
        )
        if inactive_email:
            context = {"purpose": "verification", "email": inactive_email}
            try:
                # The login flow must actually issue a verification code; merely
                # showing the code-entry page does not send an email.
                sent = _send_verification_email(self.request, customer)
                if sent:
                    messages.success(
                        self.request,
                        "کد تأیید به نشانی ایمیل شما ارسال شد. صندوق ورودی و پوشه هرزنامه را بررسی کنید.",
                    )
                else:
                    messages.warning(
                        self.request,
                        "به سقف مجاز ارسال ایمیل تأیید رسیده‌اید. پیش از درخواست دوباره، کمی صبر کنید.",
                    )
            except Exception:
                logger.exception(
                    "Could not send login-triggered verification email for customer %s",
                    customer.pk if customer else inactive_email,
                )
                messages.error(
                    self.request,
                    "در حال حاضر ارسال ایمیل تأیید ممکن نشد. تنظیمات ایمیل را بررسی و دوباره تلاش کنید.",
                )
            return render(self.request, "accounts/email_code_form.html", context)

        # Lock immediately on the fifth failed password submission, rather than
        # allowing the fifth response to look like an ordinary login failure.
        if failure_count is not None and failure_count >= self.LOGIN_FAILURE_LIMIT:
            form.add_error(
                None,
                "به‌دلیل پنج تلاش ناموفق، ورود این حساب موقتاً محدود شده است. لطفاً ۱۵ دقیقه دیگر دوباره تلاش کنید.",
            )
            return render(
                self.request,
                self.template_name,
                self.get_context_data(form=form, login_throttled=True),
                status=429,
            )

        return super().form_invalid(form)
