from uuid import uuid4

from django.test import TestCase

from accounts.models import Customer
from catalog.models import Plan, Product
from billing.models import PaymentAttempt, PaymentOrder
from billing.services import create_payment_attempt, create_payment_order
from billing.views import _replace_stale_single_plan_order


class StalePendingOrderPriceTests(TestCase):
    def setUp(self):
        self.user = Customer.objects.create_user(
            username="stale_order_user",
            email="stale-order@example.test",
            password="test-password",
        )
        self.product = Product.objects.create(
            name="Stale Order Product",
            slug="stale-order-product",
            is_active=True,
        )
        self.plan = Plan.objects.create(
            product=self.product,
            name="Silver",
            slug="silver",
            duration_unit=Plan.DurationUnit.MONTHS,
            duration_value=1,
            price_minor_units=10000,
            currency="IRR",
            device_limit=1,
            is_active=True,
        )
        self.order = create_payment_order(
            user=self.user,
            plan_id=self.plan.pk,
            idempotency_key=uuid4(),
        )

    def test_stale_order_with_unreferenced_attempt_is_canceled_and_replaced(self):
        attempt = create_payment_attempt(
            user=self.user,
            order_id=self.order.pk,
            provider="zarinpal",
            idempotency_key=uuid4(),
        )
        self.plan.price_minor_units = 100000
        self.plan.save(update_fields=["price_minor_units"])

        replacement = _replace_stale_single_plan_order(self.order, self.user)

        self.order.refresh_from_db()
        attempt.refresh_from_db()
        self.assertEqual(self.order.status, PaymentOrder.Status.CANCELED)
        self.assertEqual(attempt.status, PaymentAttempt.Status.CANCELED)
        self.assertNotEqual(replacement.pk, self.order.pk)
        self.assertEqual(replacement.status, PaymentOrder.Status.PENDING)
        self.assertEqual(replacement.amount_minor_units, 100000)
        self.assertEqual(replacement.currency, "IRR")

    def test_current_price_order_is_reused(self):
        replacement = _replace_stale_single_plan_order(self.order, self.user)
        self.assertEqual(replacement.pk, self.order.pk)
        self.assertEqual(replacement.status, PaymentOrder.Status.PENDING)

    def test_stale_order_with_provider_reference_is_not_replaced(self):
        attempt = create_payment_attempt(
            user=self.user,
            order_id=self.order.pk,
            provider="zarinpal",
            idempotency_key=uuid4(),
        )
        attempt.provider_reference = "authority-test"
        attempt.status = PaymentAttempt.Status.PENDING
        attempt.save(update_fields=["provider_reference", "status"])

        self.plan.price_minor_units = 100000
        self.plan.save(update_fields=["price_minor_units"])

        from billing.services import PaymentAttemptCreationError
        with self.assertRaises(PaymentAttemptCreationError):
            _replace_stale_single_plan_order(self.order, self.user)

        self.order.refresh_from_db()
        attempt.refresh_from_db()
        self.assertEqual(self.order.status, PaymentOrder.Status.PENDING)
        self.assertEqual(attempt.provider_reference, "authority-test")
        self.assertEqual(attempt.status, PaymentAttempt.Status.PENDING)
