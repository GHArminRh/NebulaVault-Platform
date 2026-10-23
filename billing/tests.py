
from uuid import uuid4

from django.test import TestCase

from accounts.models import User
from catalog.models import Plan, Product

from .models import PaymentAttempt, PaymentOrder
from .services import (
    IdempotencyConflict,
    OrderCreationError,
    PaymentAttemptCreationError,
    PaymentAttemptIdempotencyConflict,
    create_payment_attempt,
    create_payment_order,
)


class BillingServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="billing_user",
            email="billing@example.com",
            password="test-password-for-tests",
        )
        self.other_user = User.objects.create_user(
            username="other_user",
            email="other@example.com",
            password="test-password-for-tests",
        )

        self.product = Product.objects.create(
            name="Nebula Vault",
            slug="nebula-vault",
            is_active=True,
        )

        self.plan = Plan.objects.create(
            product=self.product,
            name="Monthly",
            slug="monthly",
            duration_unit=Plan.DurationUnit.MONTHS,
            duration_value=1,
            price_minor_units=1999,
            currency="USD",
            device_limit=2,
            is_active=True,
        )

        self.other_plan = Plan.objects.create(
            product=self.product,
            name="Yearly",
            slug="yearly",
            duration_unit=Plan.DurationUnit.YEARS,
            duration_value=1,
            price_minor_units=19999,
            currency="USD",
            device_limit=3,
            is_active=True,
        )

    def create_order(self, *, key=None, plan=None):
        return create_payment_order(
            user=self.user,
            plan_id=(plan or self.plan).pk,
            idempotency_key=key or uuid4(),
        )


class CreatePaymentOrderTests(BillingServiceTestCase):
    def test_order_uses_server_side_plan_price(self):
        order = self.create_order()

        self.assertEqual(order.user, self.user)
        self.assertEqual(order.plan, self.plan)
        self.assertEqual(order.amount_minor_units, 1999)
        self.assertEqual(order.currency, "USD")
        self.assertEqual(order.status, PaymentOrder.Status.PENDING)

    def test_same_key_and_same_plan_returns_existing_order(self):
        key = uuid4()

        first = self.create_order(key=key)
        second = self.create_order(key=key)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(
            PaymentOrder.objects.filter(
                user=self.user,
                idempotency_key=key,
            ).count(),
            1,
        )

    def test_same_key_with_different_plan_is_rejected(self):
        key = uuid4()
        self.create_order(key=key)

        with self.assertRaises(IdempotencyConflict):
            self.create_order(key=key, plan=self.other_plan)

    def test_inactive_plan_is_rejected(self):
        self.plan.is_active = False
        self.plan.save(update_fields=["is_active"])

        with self.assertRaises(OrderCreationError):
            self.create_order()

    def test_inactive_product_is_rejected(self):
        self.product.is_active = False
        self.product.save(update_fields=["is_active"])

        with self.assertRaises(OrderCreationError):
            self.create_order()

    def test_invalid_idempotency_key_is_rejected(self):
        with self.assertRaises(OrderCreationError):
            create_payment_order(
                user=self.user,
                plan_id=self.plan.pk,
                idempotency_key="not-a-uuid",
            )

    def test_inactive_user_is_rejected(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        with self.assertRaises(OrderCreationError):
            self.create_order()


class CreatePaymentAttemptTests(BillingServiceTestCase):
    def setUp(self):
        super().setUp()
        self.order = self.create_order()

    def test_attempt_copies_order_amount_and_currency(self):
        attempt = create_payment_attempt(
            user=self.user,
            order_id=self.order.pk,
            provider="ExampleProvider",
            idempotency_key=uuid4(),
        )

        self.assertEqual(attempt.order, self.order)
        self.assertEqual(attempt.provider, "exampleprovider")
        self.assertEqual(attempt.amount_minor_units, 1999)
        self.assertEqual(attempt.currency, "USD")
        self.assertEqual(attempt.status, PaymentAttempt.Status.CREATED)
        self.assertIsNotNone(attempt.idempotency_key)

    def test_another_user_cannot_start_attempt_for_order(self):
        with self.assertRaises(PaymentAttemptCreationError):
            create_payment_attempt(
                user=self.other_user,
                order_id=self.order.pk,
                provider="example",
                idempotency_key=uuid4(),
            )

        self.assertEqual(self.order.payment_attempts.count(), 0)

    def test_paid_order_cannot_start_another_attempt(self):
        self.order.status = PaymentOrder.Status.PAID
        self.order.save(update_fields=["status"])

        with self.assertRaises(PaymentAttemptCreationError):
            create_payment_attempt(
                user=self.user,
                order_id=self.order.pk,
                provider="example",
                idempotency_key=uuid4(),
            )

    def test_invalid_provider_is_rejected(self):
        with self.assertRaises(PaymentAttemptCreationError):
            create_payment_attempt(
                user=self.user,
                order_id=self.order.pk,
                provider="   ",
                idempotency_key=uuid4(),
            )

    def test_inactive_user_cannot_start_attempt(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        with self.assertRaises(PaymentAttemptCreationError):
            create_payment_attempt(
                user=self.user,
                order_id=self.order.pk,
                provider="example",
                idempotency_key=uuid4(),
            )



    def test_same_key_and_provider_returns_existing_attempt(self):
        key = uuid4()

        first = create_payment_attempt(
            user=self.user,
            order_id=self.order.pk,
            provider="example",
            idempotency_key=key,
        )
        second = create_payment_attempt(
            user=self.user,
            order_id=self.order.pk,
            provider="example",
            idempotency_key=key,
        )

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(self.order.payment_attempts.count(), 1)

    def test_same_key_with_different_provider_is_rejected(self):
        key = uuid4()

        create_payment_attempt(
            user=self.user,
            order_id=self.order.pk,
            provider="example",
            idempotency_key=key,
        )

        with self.assertRaises(PaymentAttemptIdempotencyConflict):
            create_payment_attempt(
                user=self.user,
                order_id=self.order.pk,
                provider="another-provider",
                idempotency_key=key,
            )

        self.assertEqual(self.order.payment_attempts.count(), 1)

    def test_same_key_can_be_used_for_another_order(self):
        key = uuid4()
        another_order = self.create_order(plan=self.other_plan)

        first = create_payment_attempt(
            user=self.user,
            order_id=self.order.pk,
            provider="example",
            idempotency_key=key,
        )
        second = create_payment_attempt(
            user=self.user,
            order_id=another_order.pk,
            provider="example",
            idempotency_key=key,
        )

        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(first.request_key, key)
        self.assertEqual(second.request_key, key)
