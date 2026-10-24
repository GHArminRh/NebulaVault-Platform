from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import Customer
from catalog.models import Plan, Product
from subscriptions.models import Subscription
from .services import activate_license, deactivate_license, issue_license, validate_license


class LicenseServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = Customer.objects.create_user(
            email="license-test@example.com", username="license-test", password="StrongTestPassword123!"
        )
        cls.product = Product.objects.create(name="Nebula Vault Test", slug="nebula-vault-test", is_active=True)
        cls.plan = Plan.objects.create(
            product=cls.product, name="Test Plan", slug="test-plan",
            duration_unit=Plan.DurationUnit.MONTHS, duration_value=1,
            price_minor_units=1000, currency="USD", device_limit=2, is_active=True,
        )
        now = timezone.now()
        cls.subscription = Subscription.objects.create(
            user=cls.customer, product=cls.product, kind=Subscription.Kind.PAID,
            status=Subscription.Status.ACTIVE, plan=cls.plan,
            starts_at=now - timedelta(minutes=1), expires_at=now + timedelta(days=30),
        )

    def setUp(self):
        self.license, self.plaintext_key = issue_license(self.subscription)

    def test_only_digest_is_stored_and_prefix_is_searchable(self):
        self.license.refresh_from_db()
        self.assertNotEqual(self.license.key_digest, self.plaintext_key)
        self.assertEqual(self.license.key_prefix, self.plaintext_key[:8])
        self.assertEqual(len(self.license.key_digest), 64)

    def test_activation_validation_and_deactivation(self):
        result = activate_license(self.plaintext_key, "device-fingerprint-0001", "Desktop", "1.0.0")
        self.assertTrue(result.ok)
        self.assertTrue(validate_license(self.plaintext_key, "device-fingerprint-0001").ok)
        self.assertTrue(deactivate_license(self.plaintext_key, "device-fingerprint-0001").ok)
        self.assertEqual(validate_license(self.plaintext_key, "device-fingerprint-0001").code, "device_not_activated")

    def test_device_limit_is_enforced(self):
        self.assertTrue(activate_license(self.plaintext_key, "device-fingerprint-0001").ok)
        self.assertTrue(activate_license(self.plaintext_key, "device-fingerprint-0002").ok)
        result = activate_license(self.plaintext_key, "device-fingerprint-0003")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "device_limit_reached")

    def test_suspended_license_cannot_validate(self):
        self.license.status = "suspended"
        self.license.save(update_fields=["status", "updated_at"])
        result = activate_license(self.plaintext_key, "device-fingerprint-0001")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "license_inactive")
