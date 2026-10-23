from django.test import TestCase

# Create your tests here.

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from catalog.models import Product
from subscriptions.models import Subscription, TrialRedemption
from subscriptions.services import (
    TrialAlreadyUsed,
    TrialUnavailable,
    start_trial,
)


User = get_user_model()


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
