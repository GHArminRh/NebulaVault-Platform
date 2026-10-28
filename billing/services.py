"""Compatibility facade for billing business services.

Implementations live in focused modules so existing imports from
`billing.services` remain stable while callers can gradually adopt the
more specific modules.
"""


def _is_provider_reference_integrity_error(exc):
    """Return whether an IntegrityError identifies a provider-reference clash."""
    cause = exc.__cause__
    diagnostic = getattr(cause, "diag", None)

    table_name = getattr(diagnostic, "table_name", None)
    column_name = getattr(diagnostic, "column_name", None)
    if (table_name, column_name) in {
        ("billing_paymentattempt", "provider_reference"),
        ("subscriptions_subscriptionrenewal", "payment_reference"),
    }:
        return True

    constraint_name = getattr(diagnostic, "constraint_name", None)
    if constraint_name in {
        "billing_paymentattempt_provider_reference_key",
        "subscriptions_subscriptionrenewal_payment_reference_key",
    }:
        return True

    message = str(cause or exc).lower()
    sqlite_unique_errors = (
        "unique constraint failed: billing_paymentattempt.provider_reference",
        "unique constraint failed: subscriptions_subscriptionrenewal.payment_reference",
    )
    if any(marker in message for marker in sqlite_unique_errors):
        return True

    # MySQL/MariaDB report duplicate-key violations in the exception text.
    return (
        "duplicate entry" in message
        and "for key" in message
        and (
            "provider_reference" in message
            or "payment_reference" in message
        )
    )


class OrderCreationError(Exception):
    """امکان ایجاد سفارش پرداخت درخواستی وجود ندارد."""


class IdempotencyConflict(OrderCreationError):
    """کلید جلوگیری از ثبت تکراری برای درخواست دیگری استفاده شده است."""


class PaymentAttemptCreationError(Exception):
    """امکان ایجاد تلاش پرداخت درخواستی وجود ندارد."""


class PaymentAttemptIdempotencyConflict(PaymentAttemptCreationError):
    """کلید جلوگیری از ثبت تکراری برای درخواست دیگری استفاده شده است."""


class PaymentFinalizationError(Exception):
    """امکان نهایی‌کردن پرداخت تأییدشده وجود ندارد."""


class PaymentReferenceConflict(PaymentFinalizationError):
    """شناسه پرداخت ارائه‌دهنده به‌صورت ناسازگار دوباره استفاده شده است."""


# Re-export the public service API from the focused implementation modules.
from .order_services import create_cart_payment_order, create_payment_order  # noqa: E402
from .attempt_services import create_payment_attempt  # noqa: E402
from .finalization_services import finalize_payment  # noqa: E402

__all__ = [
    "OrderCreationError",
    "IdempotencyConflict",
    "PaymentAttemptCreationError",
    "PaymentAttemptIdempotencyConflict",
    "PaymentFinalizationError",
    "PaymentReferenceConflict",
    "create_payment_order",
    "create_cart_payment_order",
    "create_payment_attempt",
    "finalize_payment",
]
