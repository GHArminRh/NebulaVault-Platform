"""Google and Apple OIDC flows isolated from the staff authentication model."""
import json
import logging
import secrets
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.db import IntegrityError, transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from .models import Customer, SocialIdentity
from .social_auth import SocialAuthNotConfigured, get_oauth_client
from .turnstile import verify_turnstile

logger = logging.getLogger(__name__)
CUSTOMER_BACKEND = "accounts.backends.CustomerAuthenticationBackend"
SOCIAL_STATE_PREFIX = "customer-social-state:"


def _enabled(provider):
    return (
        settings.SOCIAL_AUTH_GOOGLE_ENABLED if provider == "google"
        else settings.SOCIAL_AUTH_APPLE_ENABLED if provider == "apple"
        else False
    )


def _checked(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _safe_next(request, value):
    if value and url_has_allowed_host_and_scheme(
        value,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return value
    return reverse("portal:dashboard")


def _username_for_email(email):
    base = (email.partition("@")[0] or "customer").strip()[:150]
    candidate = base
    suffix = 2
    while Customer.objects.filter(username__iexact=candidate).exists():
        tail = str(suffix)
        candidate = f"{base[:150 - len(tail)]}{tail}"
        suffix += 1
    return candidate


def _verified_email(value):
    return value is True or str(value).strip().lower() in {"true", "1"}


def _failure(request, message):
    messages.error(request, message)
    return redirect("login")


@require_POST
def social_start(request, provider, flow):
    if provider not in {"google", "apple"} or flow not in {"login", "register"}:
        return _failure(request, "درخواست ورود اجتماعی معتبر نیست.")
    if not _enabled(provider):
        return _failure(request, "ورود با این سرویس هنوز پیکربندی نشده است.")

    expected_action = "customer_register" if flow == "register" else "customer_login"
    if getattr(settings, "TURNSTILE_ENABLED", True):
        valid = verify_turnstile(
            (request.POST.get("cf-turnstile-response") or "").strip(),
            secret_key=getattr(settings, "TURNSTILE_SECRET_KEY", ""),
            verify_url=getattr(
                settings,
                "TURNSTILE_VERIFY_URL",
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            ),
            expected_action=expected_action,
        )
        if not valid:
            return _failure(request, "تأیید امنیتی ناموفق بود. لطفاً کپچا را تکمیل کنید.")

    accept_terms = _checked(request.POST.get("accept_terms"))
    if flow == "register" and not accept_terms:
        return _failure(request, "برای ساخت حساب، پذیرش قوانین و مقررات الزامی است.")

    state = secrets.token_urlsafe(32)
    request.session[f"{SOCIAL_STATE_PREFIX}{state}"] = {
        "flow": flow,
        "accept_terms": accept_terms,
        "newsletter_opt_in": _checked(request.POST.get("newsletter_opt_in")),
        "next": request.POST.get("next", ""),
        "started_at": int(time.time()),
    }
    # Keep the callback on the same hostname that started the flow so the
    # browser sends the matching host-only session cookie with the OAuth state.
    callback_uri = request.build_absolute_uri(
        reverse("accounts:social_callback", kwargs={"provider": provider})
    )
    try:
        client = get_oauth_client(provider)
        options = {"state": state, "code_verifier": secrets.token_urlsafe(64)}
        if provider == "apple":
            options["response_mode"] = "form_post"
            options["response_type"] = "code id_token"
            options["nonce"] = secrets.token_urlsafe(32)
        return client.authorize_redirect(request, callback_uri, **options)
    except SocialAuthNotConfigured:
        return _failure(request, "ورود با این سرویس هنوز پیکربندی نشده است.")
    except Exception:
        logger.exception("Could not start %s customer OAuth flow", provider)
        return _failure(request, "اتصال به سرویس ورود اجتماعی برقرار نشد. دوباره تلاش کنید.")


@csrf_exempt
@require_http_methods(["GET", "POST"])
def social_callback(request, provider):
    if provider not in {"google", "apple"} or not _enabled(provider):
        return _failure(request, "پاسخ ورود اجتماعی معتبر نیست.")

    state = request.GET.get("state") or request.POST.get("state") or ""
    flow_data = request.session.pop(f"{SOCIAL_STATE_PREFIX}{state}", None)
    if not state or not flow_data or int(time.time()) - flow_data.get("started_at", 0) > 600:
        return _failure(request, "درخواست ورود منقضی یا نامعتبر است. دوباره تلاش کنید.")

    try:
        client = get_oauth_client(provider)
        token = client.authorize_access_token(request)
        claims = token.get("userinfo")
        if not claims:
            raise ValueError("Provider did not return verified OpenID user information.")
        claims = dict(claims)
        subject = str(claims.get("sub") or "").strip()
        if not subject:
            return _failure(request, "شناسه حساب دریافتی از سرویس ورود معتبر نیست.")

        apple_user = {}
        if provider == "apple" and request.method == "POST":
            try:
                apple_user = json.loads(request.POST.get("user") or "{}")
            except (TypeError, ValueError):
                apple_user = {}

        email_claim = (claims.get("email") or apple_user.get("email") or "").strip().lower()
        identity_hint = (
            SocialIdentity.objects.select_related("customer")
            .filter(provider=provider, provider_subject=subject)
            .first()
        )
        if email_claim and _verified_email(claims.get("email_verified")):
            email = email_claim
        elif identity_hint:
            # Apple may omit the email claim after the first authorization.
            # Reuse the address saved when this provider identity was verified.
            email = identity_hint.email or identity_hint.customer.email
        else:
            return _failure(request, "سرویس ارائه‌دهنده نشانی ایمیل تأییدشده‌ای ارسال نکرد.")

        first_name = (claims.get("given_name") or "").strip()
        last_name = (claims.get("family_name") or "").strip()
        if provider == "apple":
            name = apple_user.get("name") or {}
            first_name = first_name or (name.get("firstName") or "").strip()
            last_name = last_name or (name.get("lastName") or "").strip()

        now = timezone.now()
        with transaction.atomic():
            identity = (
                SocialIdentity.objects.select_related("customer")
                .filter(provider=provider, provider_subject=subject)
                .first()
            )
            if identity:
                customer = identity.customer
                identity.email = email
                identity.last_login_at = now
                identity.save(update_fields=["email", "last_login_at"])
            else:
                customer = Customer.objects.select_for_update().filter(email__iexact=email).first()
                if customer is None:
                    if flow_data.get("flow") != "register" or not flow_data.get("accept_terms"):
                        return _failure(request, "حسابی با این ایمیل پیدا نشد؛ ابتدا ثبت‌نام کنید.")
                    customer = Customer.objects.create_user(
                        email=email,
                        password=None,
                        username=_username_for_email(email),
                        first_name=first_name,
                        last_name=last_name,
                    )
                    customer.terms_accepted_at = now
                    customer.terms_version = getattr(settings, "TERMS_VERSION", "2026-11-04")
                    customer.newsletter_opt_in = bool(flow_data.get("newsletter_opt_in"))
                    customer.newsletter_opt_in_at = now if customer.newsletter_opt_in else None
                    customer.save(update_fields=[
                        "terms_accepted_at", "terms_version",
                        "newsletter_opt_in", "newsletter_opt_in_at",
                    ])
                if customer.is_banned:
                    return _failure(request, "دسترسی این حساب توسط مدیر مسدود شده است.")
                if not customer.is_active:
                    # A verified OIDC email is an alternative proof of ownership
                    # for accounts waiting for the existing email-verification step.
                    customer.is_active = True
                    customer.save(update_fields=["is_active"])
                try:
                    with transaction.atomic():
                        SocialIdentity.objects.create(
                            customer=customer,
                            provider=provider,
                            provider_subject=subject,
                            email=email,
                            last_login_at=now,
                        )
                except IntegrityError:
                    identity = SocialIdentity.objects.select_related("customer").get(
                        provider=provider,
                        provider_subject=subject,
                    )
                    customer = identity.customer

            if customer.is_banned or not customer.is_active:
                return _failure(request, "امکان ورود به این حساب وجود ندارد.")

        # Preserve the customer's configured second factor; social sign-in must
        # not silently bypass an already-enabled 2FA policy.
        if customer.two_factor_enabled or customer.email_two_factor_enabled or customer.recovery_codes:
            request.session["customer_two_factor_pending"] = {
                "user_id": str(customer.pk),
                "created_at": time.time(),
                "remember_me": True,
            }
            messages.info(request, "ورود اجتماعی تأیید شد؛ برای تکمیل ورود، عامل دوم را وارد کنید.")
            return redirect("login")

        login(request, customer, backend=CUSTOMER_BACKEND)
        request.session["ga4_pending_event"] = "login"
        messages.success(request, "ورود با حساب اجتماعی با موفقیت انجام شد.")
        return redirect(_safe_next(request, flow_data.get("next")))
    except Exception:
        logger.exception("Customer %s OAuth callback failed", provider)
        return _failure(request, "ورود اجتماعی کامل نشد. لطفاً دوباره تلاش کنید.")
