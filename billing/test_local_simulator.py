from uuid import uuid4

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Customer
from billing.models import PaymentAttempt, PaymentOrder
from catalog.models import Plan, Product
from subscriptions.models import Subscription


@override_settings(DEBUG=True, NEBULA_MOCK_PAYMENTS=True)
class LocalPaymentSimulatorTests(TestCase):
    def setUp(self):
        self.user = Customer.objects.create_user(
            username="local_simulator_user",
            email="local-simulator@example.com",
            password="test-password-for-tests",
        )
        self.product = Product.objects.create(
            name="Simulator Test Product",
            slug="simulator-test-product",
            is_active=True,
        )
        self.plan = Plan.objects.create(
            product=self.product,
            name="Test Monthly",
            slug="simulator-test-monthly",
            duration_unit=Plan.DurationUnit.MONTHS,
            duration_value=1,
            price_minor_units=1999,
            currency="USD",
            device_limit=2,
            is_active=True,
        )
        self.client.force_login(self.user)

    def start_attempt(self):
        response = self.client.post(
            reverse("billing:local_simulator_start", args=[self.plan.pk])
        )
        self.assertEqual(response.status_code, 302)
        attempt = PaymentAttempt.objects.get(provider="local_simulator")
        self.assertIn(str(attempt.pk), response.url)
        return attempt

    def test_local_simulator_page_needs_no_zarinpal_credentials(self):
        response = self.client.post(
            reverse("billing:local_simulator_start", args=[self.plan.pk])
        )
        self.assertEqual(response.status_code, 302)
        attempt = PaymentAttempt.objects.get(provider="local_simulator")
        page = self.client.get(
            reverse("billing:local_simulator", args=[attempt.pk])
        )
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "شبیه‌ساز پرداخت")
        self.assertContains(page, "شبیه‌سازی پرداخت موفق")
        self.assertContains(page, "شبیه‌سازی پرداخت ناموفق")

    def test_success_simulation_finalizes_order_and_creates_subscription(self):
        attempt = self.start_attempt()
        response = self.client.post(
            reverse("billing:local_simulator_complete", args=[attempt.pk]),
            {"simulation_result": "success"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "پرداخت آزمایشی با موفقیت شبیه‌سازی شد")
        attempt.refresh_from_db()
        attempt.order.refresh_from_db()
        self.assertEqual(attempt.status, PaymentAttempt.Status.SUCCEEDED)
        self.assertEqual(attempt.order.status, PaymentOrder.Status.PAID)
        self.assertTrue(
            Subscription.objects.filter(
                user=self.user,
                product=self.product,
                kind=Subscription.Kind.PAID,
            ).exists()
        )

    def test_failure_simulation_does_not_activate_subscription(self):
        attempt = self.start_attempt()
        response = self.client.post(
            reverse("billing:local_simulator_complete", args=[attempt.pk]),
            {"simulation_result": "failure"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "سفارش فعال نشده است")
        attempt.refresh_from_db()
        attempt.order.refresh_from_db()
        self.assertEqual(attempt.status, PaymentAttempt.Status.FAILED)
        self.assertEqual(attempt.order.status, PaymentOrder.Status.PENDING)
        self.assertFalse(Subscription.objects.filter(user=self.user).exists())

    def test_simulator_is_disabled_outside_debug_mode(self):
        with self.settings(DEBUG=False):
            response = self.client.post(
                reverse("billing:local_simulator_start", args=[self.plan.pk])
            )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(PaymentOrder.objects.exists())
        self.assertFalse(PaymentAttempt.objects.exists())

    def test_another_user_cannot_access_attempt(self):
        attempt = self.start_attempt()
        other_user = Customer.objects.create_user(
            username="other_local_simulator_user",
            email="other-local-simulator@example.com",
            password="test-password-for-tests",
        )
        self.client.force_login(other_user)
        response = self.client.get(
            reverse("billing:local_simulator", args=[attempt.pk])
        )
        self.assertEqual(response.status_code, 404)
