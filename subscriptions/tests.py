
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

from accounts.models import Customer
from django.test import TestCase
from django.utils import timezone

from catalog.models import Plan, Product
from subscriptions.models import Subscription, SubscriptionRenewal, TrialRedemption
from subscriptions.services import (
    PaymentReferenceConflict,
    RenewalNotAllowed,
    TrialAlreadyUsed,
    TrialUnavailable,
    renew_subscription,
    start_trial,
)



User = Customer


class StartTrialTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="trial-customer",
            email="trial@example.com",
            password="test-password-not-for-production",
        )
        self.product = Product.objects.create(
            name="Nebula Vault",
            slug="nebula-vault",
            is_active=True,
        )

    def test_creates_seven_day_trial(self):
        before = timezone.now()

        subscription = start_trial(
            user=self.user,
            product=self.product,
        )

        after = timezone.now()

        self.assertEqual(subscription.kind, Subscription.Kind.TRIAL)
        self.assertEqual(
            subscription.status,
            Subscription.Status.TRIALING,
        )
        self.assertIsNone(subscription.plan)
        self.assertIsNotNone(subscription.trial_redemption)

        duration = subscription.expires_at - subscription.starts_at
        self.assertEqual(duration, timedelta(days=7))

        self.assertGreaterEqual(subscription.starts_at, before)
        self.assertLessEqual(subscription.starts_at, after)

        self.assertEqual(TrialRedemption.objects.count(), 1)
        self.assertEqual(Subscription.objects.count(), 1)

    def test_cannot_redeem_trial_twice(self):
        start_trial(user=self.user, product=self.product)

        with self.assertRaises(TrialAlreadyUsed):
            start_trial(user=self.user, product=self.product)

        self.assertEqual(TrialRedemption.objects.count(), 1)
        self.assertEqual(Subscription.objects.count(), 1)

    def test_inactive_product_cannot_start_trial(self):
        self.product.is_active = False
        self.product.save(update_fields=["is_active"])

        with self.assertRaises(TrialUnavailable):
            start_trial(user=self.user, product=self.product)

        self.assertEqual(TrialRedemption.objects.count(), 0)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_inactive_user_cannot_start_trial(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        with self.assertRaises(TrialUnavailable):
            start_trial(user=self.user, product=self.product)

        self.assertEqual(TrialRedemption.objects.count(), 0)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_trial_history_remains_after_subscription_deletion_is_blocked(self):
        subscription = start_trial(
            user=self.user,
            product=self.product,
        )
        redemption = subscription.trial_redemption

        with self.assertRaises(Exception):
            redemption.delete()

        self.assertTrue(
            TrialRedemption.objects.filter(pk=redemption.pk).exists()
        )






class SubscriptionRenewalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="renewal-customer",
            email="renewal@example.com",
            password="test-password-not-for-production",
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

        self.now = datetime(
            2026, 1, 20, 12, 0, tzinfo=dt_timezone.utc
        )

    def create_paid_subscription(self, *, expires_at, status=None):
        return Subscription.objects.create(
            user=self.user,
            product=self.product,
            kind=Subscription.Kind.PAID,
            status=status or Subscription.Status.ACTIVE,
            plan=self.plan,
            trial_redemption=None,
            starts_at=expires_at - timedelta(days=30),
            expires_at=expires_at,
        )

    def renew(self, subscription, reference="payment-001", amount=1999):
        return renew_subscription(
            subscription_id=subscription.pk,
            payment_reference=reference,
            confirmed_amount_minor_units=amount,
            confirmed_currency="USD",
        )

    def test_early_renewal_preserves_remaining_time(self):
        subscription = self.create_paid_subscription(
            expires_at=datetime(
                2026, 1, 31, 12, 0, tzinfo=dt_timezone.utc
            )
        )

        with patch("subscriptions.services.timezone.now", return_value=self.now):
            renewal = self.renew(subscription)

        subscription.refresh_from_db()

        self.assertEqual(
            renewal.previous_expires_at,
            datetime(2026, 1, 31, 12, 0, tzinfo=dt_timezone.utc),
        )
        self.assertEqual(
            renewal.new_expires_at,
            datetime(2026, 2, 28, 12, 0, tzinfo=dt_timezone.utc),
        )
        self.assertEqual(subscription.expires_at, renewal.new_expires_at)
        self.assertEqual(
            subscription.status,
            Subscription.Status.ACTIVE,
        )

    def test_expired_subscription_renews_from_current_time(self):
        subscription = self.create_paid_subscription(
            expires_at=datetime(
                2026, 1, 1, 12, 0, tzinfo=dt_timezone.utc
            ),
            status=Subscription.Status.EXPIRED,
        )

        with patch("subscriptions.services.timezone.now", return_value=self.now):
            renewal = self.renew(subscription, reference="payment-002")

        subscription.refresh_from_db()

        self.assertEqual(
            renewal.new_expires_at,
            datetime(2026, 2, 20, 12, 0, tzinfo=dt_timezone.utc),
        )
        self.assertEqual(subscription.status, Subscription.Status.ACTIVE)

    def test_same_payment_reference_does_not_extend_twice(self):
        subscription = self.create_paid_subscription(
            expires_at=datetime(
                2026, 1, 31, 12, 0, tzinfo=dt_timezone.utc
            )
        )

        with patch("subscriptions.services.timezone.now", return_value=self.now):
            first = self.renew(subscription, reference="payment-003")
            second = self.renew(subscription, reference="payment-003")

        subscription.refresh_from_db()

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(SubscriptionRenewal.objects.count(), 1)
        self.assertEqual(subscription.expires_at, first.new_expires_at)

    def test_wrong_amount_is_rejected(self):
        subscription = self.create_paid_subscription(
            expires_at=datetime(
                2026, 1, 31, 12, 0, tzinfo=dt_timezone.utc
            )
        )

        with patch("subscriptions.services.timezone.now", return_value=self.now):
            with self.assertRaises(RenewalNotAllowed):
                self.renew(
                    subscription,
                    reference="payment-004",
                    amount=100,
                )

        self.assertEqual(SubscriptionRenewal.objects.count(), 0)

    def test_canceled_subscription_cannot_be_renewed(self):
        subscription = self.create_paid_subscription(
            expires_at=datetime(
                2026, 1, 31, 12, 0, tzinfo=dt_timezone.utc
            ),
            status=Subscription.Status.CANCELED,
        )

        with patch("subscriptions.services.timezone.now", return_value=self.now):
            with self.assertRaises(RenewalNotAllowed):
                self.renew(subscription, reference="payment-005")

        self.assertEqual(SubscriptionRenewal.objects.count(), 0)

    def test_payment_reference_cannot_be_reused_for_another_subscription(self):
        first_subscription = self.create_paid_subscription(
            expires_at=datetime(
                2026, 1, 31, 12, 0, tzinfo=dt_timezone.utc
            )
        )

        second_subscription = self.create_paid_subscription(
            expires_at=datetime(
                2026, 3, 31, 12, 0, tzinfo=dt_timezone.utc
            )
        )

        with patch("subscriptions.services.timezone.now", return_value=self.now):
            self.renew(first_subscription, reference="payment-006")

            with self.assertRaises(PaymentReferenceConflict):
                self.renew(second_subscription, reference="payment-006")

        self.assertEqual(SubscriptionRenewal.objects.count(), 1)
