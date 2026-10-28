import json
from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from accounts.models import Customer
from catalog.models import Plan, Product
from subscriptions.models import Subscription
from .services import activate_license, deactivate_license, issue_license, validate_license


class LicenseFixtures:
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


class LicenseServiceTests(LicenseFixtures, TestCase):
    def setUp(self):
        self.license, self.plaintext_key = issue_license(self.subscription)

    def test_only_digest_and_encrypted_recoverable_key_are_stored(self):
        self.license.refresh_from_db()
        self.assertNotEqual(self.license.key_digest, self.plaintext_key)
        self.assertEqual(self.license.key_prefix, self.plaintext_key[:8])
        self.assertEqual(len(self.license.key_digest), 64)
        self.assertNotIn(self.plaintext_key, self.license.notes)
        self.assertEqual(self.license.display_key, self.plaintext_key)

    def test_activation_validation_and_deactivation(self):
        result = activate_license(self.plaintext_key, "device-fingerprint-0001", "Desktop", "1.0.0")
        self.assertTrue(result.ok)
        self.assertTrue(validate_license(self.plaintext_key, "device-fingerprint-0001").ok)
        self.assertTrue(deactivate_license(self.plaintext_key, "device-fingerprint-0001").ok)
        self.assertEqual(validate_license(self.plaintext_key, "device-fingerprint-0001").code, "device_not_activated")

    def test_paid_term_begins_at_first_activation_even_if_purchase_date_passed(self):
        activation_time = timezone.now()
        self.plan.duration_value = 2
        self.plan.save(update_fields=["duration_value"])
        self.subscription.starts_at = activation_time - timedelta(days=90)
        self.subscription.expires_at = activation_time - timedelta(days=60)
        self.subscription.save(update_fields=["starts_at", "expires_at"])

        with patch("licensing.services.timezone.now", return_value=activation_time):
            result = activate_license(
                self.plaintext_key, "device-fingerprint-first-start", "Desktop", "1.0.0"
            )

        self.assertTrue(result.ok)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.starts_at, activation_time)

        from subscriptions.services import _add_plan_duration
        self.assertEqual(
            self.subscription.expires_at,
            _add_plan_duration(activation_time, self.plan),
        )
        self.assertEqual(result.activation.first_activated_at, activation_time)

    def test_reactivating_same_device_does_not_restart_paid_term(self):
        first_time = timezone.now()
        with patch("licensing.services.timezone.now", return_value=first_time):
            first = activate_license(
                self.plaintext_key, "device-fingerprint-stable", "Desktop", "1.0.0"
            )
        self.assertTrue(first.ok)
        self.subscription.refresh_from_db()
        original_expiry = self.subscription.expires_at

        with patch("licensing.services.timezone.now", return_value=first_time + timedelta(days=3)):
            second = activate_license(
                self.plaintext_key, "device-fingerprint-stable", "Desktop", "1.0.0"
            )

        self.assertTrue(second.ok)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.expires_at, original_expiry)

    def test_second_device_and_reactivation_do_not_restart_paid_term(self):
        first_time = timezone.now()
        with patch("licensing.services.timezone.now", return_value=first_time):
            first = activate_license(
                self.plaintext_key, "device-fingerprint-primary", "Desktop", "1.0.0"
            )
        self.assertTrue(first.ok)
        self.subscription.refresh_from_db()
        original_expiry = self.subscription.expires_at

        with patch("licensing.services.timezone.now", return_value=first_time + timedelta(days=2)):
            second_device = activate_license(
                self.plaintext_key, "device-fingerprint-secondary", "Laptop", "1.0.0"
            )
        self.assertTrue(second_device.ok)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.expires_at, original_expiry)

        with patch("licensing.services.timezone.now", return_value=first_time + timedelta(days=3)):
            deactivated = deactivate_license(
                self.plaintext_key, "device-fingerprint-primary"
            )
        self.assertTrue(deactivated.ok)

        with patch("licensing.services.timezone.now", return_value=first_time + timedelta(days=4)):
            reactivated = activate_license(
                self.plaintext_key, "device-fingerprint-primary", "Desktop", "1.0.0"
            )
        self.assertFalse(reactivated.ok)
        self.assertEqual(reactivated.code, "device_deactivated")
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.expires_at, original_expiry)

    def test_device_limit_is_enforced_and_deactivation_frees_slot(self):
        self.assertTrue(activate_license(self.plaintext_key, "device-fingerprint-0001").ok)
        self.assertTrue(activate_license(self.plaintext_key, "device-fingerprint-0002").ok)
        result = activate_license(self.plaintext_key, "device-fingerprint-0003")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "device_limit_reached")
        self.assertTrue(deactivate_license(self.plaintext_key, "device-fingerprint-0001").ok)
        self.assertEqual(
            activate_license(self.plaintext_key, "device-fingerprint-0001").code,
            "device_deactivated",
        )
        self.assertTrue(activate_license(self.plaintext_key, "device-fingerprint-0003").ok)

    def test_suspended_license_cannot_activate_or_validate(self):
        self.license.status = "suspended"
        self.license.save(update_fields=["status", "updated_at"])
        result = activate_license(self.plaintext_key, "device-fingerprint-0001")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "license_suspended")

    def test_revoked_license_can_still_deactivate_device(self):
        self.assertTrue(activate_license(self.plaintext_key, "device-fingerprint-0001").ok)
        self.license.status = "revoked"
        self.license.save(update_fields=["status", "updated_at"])
        self.assertTrue(deactivate_license(self.plaintext_key, "device-fingerprint-0001").ok)

    def test_invalid_key_and_fingerprint_are_rejected(self):
        self.assertEqual(activate_license("not-a-key", "device-fingerprint-0001").code, "invalid_license")
        self.assertEqual(activate_license(self.plaintext_key, "short").code, "invalid_device")
        self.assertEqual(validate_license(self.plaintext_key, None).code, "invalid_device")


class LicenseAPITests(LicenseFixtures, TestCase):
    def setUp(self):
        cache.clear()
        self.license, self.plaintext_key = issue_license(self.subscription)
        self.fingerprint = "device-fingerprint-api-0001"

    def post_json(self, path, payload):
        return self.client.post(
            f"/api/licensing/{path}/",
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_activate_validate_and_deactivate_endpoints(self):
        payload = {
            "license_key": self.plaintext_key,
            "device_fingerprint": self.fingerprint,
            "device_name": "Test workstation",
            "app_version": "1.0.0",
        }
        activated = self.post_json("activate", payload)
        self.assertEqual(activated.status_code, 200)
        self.assertTrue(activated.json()["ok"])
        self.assertEqual(activated.json()["device_limit"], 2)
        self.subscription.refresh_from_db()
        self.assertEqual(
            activated.json()["expires_at"],
            self.subscription.expires_at.isoformat(),
        )
        self.assertEqual(
            activated.json()["starts_at"],
            self.subscription.starts_at.isoformat(),
        )
        self.assertIsNotNone(activated.json()["first_activated_at"])
        self.assertEqual(activated["Cache-Control"], "no-store")

        validated = self.post_json("validate", payload)
        self.assertEqual(validated.status_code, 200)
        self.assertEqual(validated.json()["code"], "valid")

        deactivated = self.post_json("deactivate", payload)
        self.assertEqual(deactivated.status_code, 200)
        self.assertEqual(deactivated.json()["code"], "deactivated")

        invalidated = self.post_json("validate", payload)
        self.assertEqual(invalidated.status_code, 403)
        self.assertEqual(invalidated.json()["code"], "device_not_activated")

    def test_malformed_and_oversized_payloads_are_rejected(self):
        malformed = self.client.post(
            "/api/licensing/activate/", data="{not-json", content_type="application/json"
        )
        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(malformed.json()["code"], "invalid_request")

        oversized = self.client.post(
            "/api/licensing/activate/",
            data=json.dumps({"padding": "x" * (16 * 1024)}),
            content_type="application/json",
        )
        self.assertEqual(oversized.status_code, 400)
        self.assertEqual(oversized.json()["code"], "invalid_request")

    def test_non_post_requests_are_rejected(self):
        response = self.client.get("/api/licensing/activate/")
        self.assertEqual(response.status_code, 405)

    @patch("licensing.views._rate_limited", return_value=True)
    def test_rate_limited_requests_are_rejected(self, mocked_rate_limit):
        response = self.post_json("activate", {})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["code"], "rate_limited")
