import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4
from unittest.mock import patch
from django.db import IntegrityError, close_old_connections, connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone

from accounts.models import Customer

User = Customer
from catalog.models import Plan, Product
from subscriptions.models import Subscription, SubscriptionRenewal
from licensing.models import License

from .models import PaymentAttempt, PaymentOrder
from .services import (
    IdempotencyConflict,
    OrderCreationError,
    PaymentAttemptCreationError,
    PaymentAttemptIdempotencyConflict,
    PaymentFinalizationError,
    PaymentReferenceConflict,
    create_payment_attempt,
    create_payment_order,
    finalize_payment,
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

    def create_order(self, *, key=None, plan=None, subscription=None):
        return create_payment_order(
            user=self.user,
            plan_id=(plan or self.plan).pk,
            idempotency_key=key or uuid4(),
            subscription_id=(
                subscription.pk if subscription is not None else None
            ),
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

    def test_same_key_cannot_switch_from_explicit_to_automatic_subscription(self):
        subscription = Subscription.objects.create(
            user=self.user,
            product=self.product,
            kind=Subscription.Kind.PAID,
            status=Subscription.Status.ACTIVE,
            plan=self.plan,
            starts_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=10),
        )
        key = uuid4()

        first_order = self.create_order(key=key, subscription=subscription)

        self.assertTrue(first_order.subscription_id_was_explicit)
        with self.assertRaises(IdempotencyConflict):
            self.create_order(key=key)

        self.assertEqual(
            PaymentOrder.objects.filter(
                user=self.user,
                idempotency_key=key,
            ).count(),
            1,
        )

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

    def test_renewal_order_is_linked_to_subscription(self):
        subscription = Subscription.objects.create(
            user=self.user,
            product=self.product,
            kind=Subscription.Kind.PAID,
            status=Subscription.Status.ACTIVE,
            plan=self.plan,
            starts_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=10),
        )

        order = self.create_order(subscription=subscription)

        self.assertEqual(order.subscription, subscription)
        self.assertEqual(order.plan, subscription.plan)
        self.assertEqual(order.amount_minor_units, self.plan.price_minor_units)

    def test_another_users_subscription_cannot_be_renewed(self):
        subscription = Subscription.objects.create(
            user=self.other_user,
            product=self.product,
            kind=Subscription.Kind.PAID,
            status=Subscription.Status.ACTIVE,
            plan=self.plan,
            starts_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=10),
        )

        with self.assertRaises(OrderCreationError):
            self.create_order(subscription=subscription)

        self.assertEqual(PaymentOrder.objects.count(), 0)

    def test_renewal_order_rejects_a_different_plan(self):
        subscription = Subscription.objects.create(
            user=self.user,
            product=self.product,
            kind=Subscription.Kind.PAID,
            status=Subscription.Status.ACTIVE,
            plan=self.plan,
            starts_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=10),
        )

        with self.assertRaises(OrderCreationError):
            self.create_order(
                plan=self.other_plan,
                subscription=subscription,
            )

        self.assertEqual(PaymentOrder.objects.count(), 0)

    def test_canceled_subscription_cannot_be_renewed(self):
        subscription = Subscription.objects.create(
            user=self.user,
            product=self.product,
            kind=Subscription.Kind.PAID,
            status=Subscription.Status.CANCELED,
            plan=self.plan,
            starts_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=10),
        )

        with self.assertRaises(OrderCreationError):
            self.create_order(subscription=subscription)

        self.assertEqual(PaymentOrder.objects.count(), 0)

    def test_same_idempotency_key_cannot_target_another_subscription(self):
        first_subscription = Subscription.objects.create(
            user=self.user,
            product=self.product,
            kind=Subscription.Kind.PAID,
            status=Subscription.Status.ACTIVE,
            plan=self.plan,
            starts_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=10),
        )
        second_subscription = Subscription.objects.create(
            user=self.user,
            product=self.product,
            kind=Subscription.Kind.PAID,
            status=Subscription.Status.ACTIVE,
            plan=self.plan,
            starts_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=20),
        )
        key = uuid4()

        first_order = self.create_order(
            key=key,
            subscription=first_subscription,
        )

        with self.assertRaises(IdempotencyConflict):
            self.create_order(
                key=key,
                subscription=second_subscription,
            )

        self.assertEqual(PaymentOrder.objects.count(), 1)
        self.assertEqual(first_order.subscription, first_subscription)


    def test_existing_paid_subscription_is_selected_for_renewal(self):
        subscription = Subscription.objects.create(
            user=self.user,
            product=self.product,
            kind=Subscription.Kind.PAID,
            status=Subscription.Status.ACTIVE,
            plan=self.plan,
            starts_at=timezone.now() - timedelta(days=10),
            expires_at=timezone.now() + timedelta(days=20),
        )

        order = self.create_order()

        self.assertEqual(order.subscription, subscription)

    def test_expired_paid_subscription_is_selected_for_renewal(self):
        subscription = Subscription.objects.create(
            user=self.user,
            product=self.product,
            kind=Subscription.Kind.PAID,
            status=Subscription.Status.EXPIRED,
            plan=self.plan,
            starts_at=timezone.now() - timedelta(days=40),
            expires_at=timezone.now() - timedelta(days=10),
        )

        order = self.create_order()

        self.assertEqual(order.subscription, subscription)

    def test_canceled_subscription_is_not_selected_for_renewal(self):
        Subscription.objects.create(
            user=self.user,
            product=self.product,
            kind=Subscription.Kind.PAID,
            status=Subscription.Status.CANCELED,
            plan=self.plan,
            starts_at=timezone.now() - timedelta(days=40),
            expires_at=timezone.now() - timedelta(days=10),
        )

        order = self.create_order()

        self.assertIsNone(order.subscription)

    def test_multiple_paid_subscriptions_make_automatic_selection_ambiguous(self):
        for days in (10, 20):
            Subscription.objects.create(
                user=self.user,
                product=self.product,
                kind=Subscription.Kind.PAID,
                status=Subscription.Status.ACTIVE,
                plan=self.plan,
                starts_at=timezone.now() - timedelta(days=5),
                expires_at=timezone.now() + timedelta(days=days),
            )

        with self.assertRaises(OrderCreationError):
            self.create_order()


    def test_pending_initial_order_blocks_a_second_order_with_new_key(self):
        first_order = self.create_order()

        with self.assertRaises(OrderCreationError):
            self.create_order()

        self.assertEqual(
            PaymentOrder.objects.filter(
                user=self.user,
                plan=self.plan,
                status=PaymentOrder.Status.PENDING,
                subscription__isnull=True,
            ).count(),
            1,
        )
        first_order.refresh_from_db()
        self.assertEqual(first_order.status, PaymentOrder.Status.PENDING)

    def test_pending_renewal_order_blocks_a_second_order_for_same_subscription(self):
        subscription = Subscription.objects.create(
            user=self.user,
            product=self.product,
            kind=Subscription.Kind.PAID,
            status=Subscription.Status.ACTIVE,
            plan=self.plan,
            starts_at=timezone.now() - timedelta(days=5),
            expires_at=timezone.now() + timedelta(days=25),
        )
        first_order = self.create_order(subscription=subscription)

        with self.assertRaises(OrderCreationError):
            self.create_order(subscription=subscription)

        self.assertEqual(
            PaymentOrder.objects.filter(
                user=self.user,
                subscription=subscription,
                status=PaymentOrder.Status.PENDING,
            ).count(),
            1,
        )
        first_order.refresh_from_db()
        self.assertEqual(first_order.status, PaymentOrder.Status.PENDING)

    def test_canceled_initial_order_does_not_block_a_new_order(self):
        first_order = self.create_order()
        first_order.status = PaymentOrder.Status.CANCELED
        first_order.save(update_fields=["status"])

        second_order = self.create_order()

        self.assertNotEqual(first_order.pk, second_order.pk)
        self.assertEqual(second_order.status, PaymentOrder.Status.PENDING)
        self.assertIsNone(second_order.subscription)

    def test_expired_initial_order_does_not_block_a_new_order(self):
        first_order = self.create_order()
        first_order.status = PaymentOrder.Status.EXPIRED
        first_order.save(update_fields=["status"])

        second_order = self.create_order()

        self.assertNotEqual(first_order.pk, second_order.pk)
        self.assertEqual(second_order.status, PaymentOrder.Status.PENDING)
        self.assertIsNone(second_order.subscription)



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

    def test_boolean_order_id_is_rejected(self):
        with self.assertRaises(PaymentAttemptCreationError):
            create_payment_attempt(
                user=self.user,
                order_id=True,
                provider="test",
                idempotency_key=uuid4(),
            )




class FinalizePaymentTests(BillingServiceTestCase):
    def setUp(self):
        super().setUp()
        self.order = self.create_order()
        self.attempt = create_payment_attempt(
            user=self.user,
            order_id=self.order.pk,
            provider="example",
            idempotency_key=uuid4(),
        )

    def finalize(self, **overrides):
        data = {
            "attempt_id": self.attempt.pk,
            "provider_reference": "provider-ref-001",
            "confirmed_amount_minor_units": self.order.amount_minor_units,
            "confirmed_currency": self.order.currency,
        }
        data.update(overrides)
        return finalize_payment(**data)

    def test_nonexistent_attempt_is_rejected(self):
        with self.assertRaises(PaymentFinalizationError):
            finalize_payment(
                attempt_id=999999,
                provider_reference="provider-ref-missing",
                confirmed_amount_minor_units=self.order.amount_minor_units,
                confirmed_currency=self.order.currency,
            )

    def test_invalid_attempt_id_is_rejected(self):
        with self.assertRaises(PaymentFinalizationError):
            finalize_payment(
                attempt_id="not-an-id",
                provider_reference="provider-ref-invalid-id",
                confirmed_amount_minor_units=self.order.amount_minor_units,
                confirmed_currency=self.order.currency,
            )

    def test_empty_provider_reference_is_rejected(self):
        with self.assertRaises(PaymentFinalizationError):
            self.finalize(provider_reference="   ")

        self.order.refresh_from_db()
        self.attempt.refresh_from_db()

        self.assertEqual(self.order.status, PaymentOrder.Status.PENDING)
        self.assertEqual(self.attempt.status, PaymentAttempt.Status.CREATED)

    def test_invalid_confirmed_currency_is_rejected(self):
        for currency in ("US", "ÜSD", "ریال"):
            with self.subTest(currency=currency):
                with self.assertRaises(PaymentFinalizationError):
                    self.finalize(confirmed_currency=currency)

                self.order.refresh_from_db()
                self.attempt.refresh_from_db()

                self.assertEqual(
                    self.order.status,
                    PaymentOrder.Status.PENDING,
                )
                self.assertEqual(
                    self.attempt.status,
                    PaymentAttempt.Status.CREATED,
                )
                self.assertEqual(Subscription.objects.count(), 0)
    def test_canceled_attempt_cannot_be_finalized(self):
        self.attempt.status = PaymentAttempt.Status.CANCELED
        self.attempt.save(update_fields=["status"])

        with self.assertRaises(PaymentFinalizationError):
            self.finalize()

        self.order.refresh_from_db()
        self.attempt.refresh_from_db()

        self.assertEqual(self.order.status, PaymentOrder.Status.PENDING)
        self.assertEqual(self.attempt.status, PaymentAttempt.Status.CANCELED)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_failed_attempt_cannot_be_finalized(self):
        self.attempt.status = PaymentAttempt.Status.FAILED
        self.attempt.save(update_fields=["status"])

        with self.assertRaises(PaymentFinalizationError):
            self.finalize()

        self.order.refresh_from_db()
        self.attempt.refresh_from_db()

        self.assertEqual(self.order.status, PaymentOrder.Status.PENDING)
        self.assertEqual(self.attempt.status, PaymentAttempt.Status.FAILED)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_successful_initial_purchase_creates_paid_subscription(self):
        attempt = self.finalize()

        self.order.refresh_from_db()
        self.attempt.refresh_from_db()

        subscription = self.order.subscription
        subscription.refresh_from_db()

        self.assertEqual(attempt.pk, self.attempt.pk)
        self.assertEqual(self.order.status, PaymentOrder.Status.PAID)
        self.assertEqual(self.attempt.status, PaymentAttempt.Status.SUCCEEDED)
        self.assertEqual(self.attempt.provider_reference, "provider-ref-001")
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.plan, self.plan)
        self.assertEqual(subscription.kind, Subscription.Kind.PAID)
        self.assertEqual(subscription.status, Subscription.Status.ACTIVE)
        self.assertEqual(
            Subscription.objects.filter(user=self.user, plan=self.plan).count(),
            1,
        )
        license_record = License.objects.get(subscription=subscription)
        self.assertTrue(attempt.issued_license_key.startswith("NVL-"))
        self.assertNotEqual(license_record.key_digest, attempt.issued_license_key)
        self.assertEqual(license_record.key_prefix, attempt.issued_license_key[:8])
        self.assertEqual(License.objects.filter(subscription=subscription).count(), 1)

    def test_wrong_amount_is_rejected_without_mutation(self):
        with self.assertRaises(PaymentFinalizationError):
            self.finalize(confirmed_amount_minor_units=self.order.amount_minor_units + 1)

        self.order.refresh_from_db()
        self.attempt.refresh_from_db()

        self.assertEqual(self.order.status, PaymentOrder.Status.PENDING)
        self.assertEqual(self.attempt.status, PaymentAttempt.Status.CREATED)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_wrong_currency_is_rejected_without_mutation(self):
        with self.assertRaises(PaymentFinalizationError):
            self.finalize(confirmed_currency="EUR")

        self.order.refresh_from_db()
        self.attempt.refresh_from_db()

        self.assertEqual(self.order.status, PaymentOrder.Status.PENDING)
        self.assertEqual(self.attempt.status, PaymentAttempt.Status.CREATED)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_duplicate_callback_does_not_create_second_subscription(self):
        first = self.finalize()
        second = self.finalize()

        self.assertEqual(first.pk, second.pk)
        self.assertTrue(first.issued_license_key)
        self.assertFalse(hasattr(second, "issued_license_key"))
        self.assertEqual(
            Subscription.objects.filter(user=self.user, plan=self.plan).count(),
            1,
        )
        self.assertEqual(License.objects.count(), 1)

    def test_changed_plan_price_does_not_change_existing_order_amount(self):
        original_amount = self.order.amount_minor_units

        self.plan.price_minor_units = original_amount + 500
        self.plan.save(update_fields=["price_minor_units"])

        self.finalize()

        self.order.refresh_from_db()
        self.assertEqual(self.order.amount_minor_units, original_amount)
        self.assertEqual(self.order.status, PaymentOrder.Status.PAID)

    def test_provider_reference_cannot_be_reused_for_another_attempt(self):
        self.finalize()

        another_order = self.create_order(plan=self.other_plan)
        another_attempt = create_payment_attempt(
            user=self.user,
            order_id=another_order.pk,
            provider="example",
            idempotency_key=uuid4(),
        )

        with self.assertRaises(PaymentReferenceConflict):
            finalize_payment(
                attempt_id=another_attempt.pk,
                provider_reference="provider-ref-001",
                confirmed_amount_minor_units=another_order.amount_minor_units,
                confirmed_currency=another_order.currency,
            )

        another_order.refresh_from_db()
        another_attempt.refresh_from_db()

        self.assertEqual(another_order.status, PaymentOrder.Status.PENDING)
        self.assertEqual(another_attempt.status, PaymentAttempt.Status.CREATED)

    def test_unrelated_integrity_error_is_not_converted_to_reference_conflict(self):
        with patch.object(
            PaymentOrder,
            "save",
            side_effect=IntegrityError("unrelated integrity failure"),
        ):
            with self.assertRaisesRegex(
                IntegrityError,
                "unrelated integrity failure",
            ):
                self.finalize()

        self.order.refresh_from_db()
        self.attempt.refresh_from_db()

        self.assertEqual(self.order.status, PaymentOrder.Status.PENDING)
        self.assertEqual(self.attempt.status, PaymentAttempt.Status.CREATED)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_successful_renewal_records_renewal_and_extends_subscription(self):
        subscription = Subscription.objects.create(
            user=self.user,
            product=self.product,
            kind=Subscription.Kind.PAID,
            status=Subscription.Status.ACTIVE,
            plan=self.plan,
            starts_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=10),
        )

        renewal_order = self.create_order(subscription=subscription)

        renewal_attempt = create_payment_attempt(
            user=self.user,
            order_id=renewal_order.pk,
            provider="example",
            idempotency_key=uuid4(),
        )

        previous_expiry = subscription.expires_at

        finalized_attempt = finalize_payment(
            attempt_id=renewal_attempt.pk,
            provider_reference="provider-renewal-001",
            confirmed_amount_minor_units=renewal_order.amount_minor_units,
            confirmed_currency=renewal_order.currency,
        )

        subscription.refresh_from_db()
        renewal_order.refresh_from_db()

        self.assertEqual(renewal_order.status, PaymentOrder.Status.PAID)
        self.assertGreater(subscription.expires_at, previous_expiry)
        self.assertEqual(subscription.status, Subscription.Status.ACTIVE)

        renewal = SubscriptionRenewal.objects.get(
            payment_reference="provider-renewal-001"
        )
        self.assertEqual(renewal.subscription, subscription)
        self.assertEqual(renewal.amount_minor_units, renewal_order.amount_minor_units)
        self.assertEqual(renewal.currency, renewal_order.currency)
        # finalize_payment loads and returns its own locked model instance;
        # delivery-only attributes belong to that returned instance, not this stale one.
        self.assertTrue(hasattr(finalized_attempt, "issued_license_key"))
        self.assertTrue(finalized_attempt.issued_license_key)
        self.assertEqual(License.objects.filter(subscription=subscription).count(), 1)

    def test_duplicate_renewal_callback_does_not_extend_twice(self):
        subscription = Subscription.objects.create(
            user=self.user,
            product=self.product,
            kind=Subscription.Kind.PAID,
            status=Subscription.Status.ACTIVE,
            plan=self.plan,
            starts_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=10),
        )

        renewal_order = self.create_order(subscription=subscription)

        renewal_attempt = create_payment_attempt(
            user=self.user,
            order_id=renewal_order.pk,
            provider="example",
            idempotency_key=uuid4(),
        )

        callback = {
            "attempt_id": renewal_attempt.pk,
            "provider_reference": "provider-renewal-duplicate",
            "confirmed_amount_minor_units": renewal_order.amount_minor_units,
            "confirmed_currency": renewal_order.currency,
        }

        finalize_payment(**callback)
        subscription.refresh_from_db()
        expiry_after_first = subscription.expires_at

        finalize_payment(**callback)
        subscription.refresh_from_db()

        self.assertEqual(subscription.expires_at, expiry_after_first)
        self.assertEqual(
            SubscriptionRenewal.objects.filter(
                subscription=subscription
            ).count(),
            1,
        )


    def test_another_users_subscription_cannot_be_renewed(self):
        subscription = Subscription.objects.create(
            user=self.other_user,
            product=self.product,
            kind=Subscription.Kind.PAID,
            status=Subscription.Status.ACTIVE,
            plan=self.plan,
            starts_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=10),
        )

        self.order.subscription = subscription
        self.order.save(update_fields=["subscription"])

        with self.assertRaises(PaymentFinalizationError):
            self.finalize(
                provider_reference="provider-other-user",
            )

        self.order.refresh_from_db()
        self.attempt.refresh_from_db()

        self.assertEqual(self.order.status, PaymentOrder.Status.PENDING)
        self.assertEqual(self.attempt.status, PaymentAttempt.Status.CREATED)
        self.assertEqual(
            SubscriptionRenewal.objects.filter(
                subscription=subscription
            ).count(),
            0,
        )

    def test_canceled_subscription_cannot_be_renewed_during_finalization(self):
        subscription = Subscription.objects.create(
            user=self.user,
            product=self.product,
            kind=Subscription.Kind.PAID,
            status=Subscription.Status.ACTIVE,
            plan=self.plan,
            starts_at=timezone.now() - timedelta(days=5),
            expires_at=timezone.now() + timedelta(days=25),
        )
        order = self.create_order(subscription=subscription)
        attempt = create_payment_attempt(
            user=self.user,
            order_id=order.pk,
            provider="test",
            idempotency_key=uuid4(),
        )

        subscription.status = Subscription.Status.CANCELED
        subscription.save(update_fields=["status", "updated_at"])

        original_expiry = subscription.expires_at

        with self.assertRaises(PaymentFinalizationError):
            finalize_payment(
                attempt_id=attempt.pk,
                provider_reference="cancelled-subscription-ref",
                confirmed_amount_minor_units=order.amount_minor_units,
                confirmed_currency=order.currency,
            )

        subscription.refresh_from_db()
        order.refresh_from_db()
        attempt.refresh_from_db()

        self.assertEqual(subscription.status, Subscription.Status.CANCELED)
        self.assertEqual(subscription.expires_at, original_expiry)
        self.assertEqual(order.status, PaymentOrder.Status.PENDING)
        self.assertEqual(attempt.status, PaymentAttempt.Status.CREATED)
        self.assertIsNone(attempt.provider_reference)
        self.assertFalse(
            SubscriptionRenewal.objects.filter(
                payment_reference="cancelled-subscription-ref"
            ).exists()
        )

    def test_boolean_attempt_id_is_rejected(self):
        with self.assertRaises(PaymentFinalizationError):
            finalize_payment(
                attempt_id=True,
                provider_reference="boolean-attempt-id-ref",
                confirmed_amount_minor_units=1999,
                confirmed_currency="USD",
            )

@skipUnlessDBFeature("has_select_for_update")
class ConcurrentPaymentOrderTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user = User.objects.create_user(
            username="concurrent_billing_user",
            email="concurrent-billing@example.com",
            password="test-password-for-tests",
        )
        self.product = Product.objects.create(
            name="Concurrent Nebula Vault",
            slug="concurrent-nebula-vault",
            is_active=True,
        )
        self.plan = Plan.objects.create(
            product=self.product,
            name="Monthly",
            slug="concurrent-monthly",
            duration_unit=Plan.DurationUnit.MONTHS,
            duration_value=1,
            price_minor_units=1999,
            currency="USD",
            device_limit=2,
            is_active=True,
        )

    def _create_order(self, barrier):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return create_payment_order(
                user=self.user,
                plan_id=self.plan.pk,
                idempotency_key=uuid4(),
            )
        except OrderCreationError as exc:
            return exc
        finally:
            connections.close_all()

    def test_concurrent_initial_purchase_creates_only_one_pending_order(self):
        barrier = threading.Barrier(2)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(self._create_order, barrier)
                for _ in range(2)
            ]
            results = [future.result(timeout=20) for future in futures]

        created_orders = [
            result
            for result in results
            if isinstance(result, PaymentOrder)
        ]
        rejected_requests = [
            result
            for result in results
            if isinstance(result, OrderCreationError)
        ]

        self.assertEqual(len(created_orders), 1)
        self.assertEqual(len(rejected_requests), 1)

        self.assertEqual(
            PaymentOrder.objects.filter(
                user=self.user,
                plan=self.plan,
                subscription__isnull=True,
                status=PaymentOrder.Status.PENDING,
            ).count(),
            1,
        )

@skipUnlessDBFeature("has_select_for_update")
class ConcurrentPaymentFinalizationTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user = User.objects.create_user(
            username="concurrent_finalization_user",
            email="concurrent-finalization@example.com",
            password="test-password-for-tests",
        )
        self.product = Product.objects.create(
            name="Concurrent Finalization Product",
            slug="concurrent-finalization-product",
            is_active=True,
        )
        self.plan = Plan.objects.create(
            product=self.product,
            name="Monthly",
            slug="concurrent-finalization-monthly",
            duration_unit=Plan.DurationUnit.MONTHS,
            duration_value=1,
            price_minor_units=1999,
            currency="USD",
            device_limit=2,
            is_active=True,
        )
        self.order = create_payment_order(
            user=self.user,
            plan_id=self.plan.pk,
            idempotency_key=uuid4(),
        )
        self.attempt = create_payment_attempt(
            user=self.user,
            order_id=self.order.pk,
            provider="example",
            idempotency_key=uuid4(),
        )

    def _finalize(self, barrier):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return finalize_payment(
                attempt_id=self.attempt.pk,
                provider_reference="concurrent-provider-reference",
                confirmed_amount_minor_units=self.order.amount_minor_units,
                confirmed_currency=self.order.currency,
            )
        finally:
            connections.close_all()

    def test_concurrent_duplicate_callbacks_finalize_only_once(self):
        barrier = threading.Barrier(2)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(self._finalize, barrier)
                for _ in range(2)
            ]
            results = [future.result(timeout=20) for future in futures]

        self.assertEqual(results[0].pk, self.attempt.pk)
        self.assertEqual(results[1].pk, self.attempt.pk)

        self.order.refresh_from_db()
        self.attempt.refresh_from_db()

        self.assertEqual(self.order.status, PaymentOrder.Status.PAID)
        self.assertEqual(self.attempt.status, PaymentAttempt.Status.SUCCEEDED)
        self.assertEqual(
            Subscription.objects.filter(
                user=self.user,
                product=self.product,
                kind=Subscription.Kind.PAID,
            ).count(),
            1,
        )
