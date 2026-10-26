from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Customer
from billing.models import PaymentAttempt, PaymentOrder
from billing.services import create_payment_order
from catalog.models import Plan, Product


@override_settings(DEBUG=True, NEBULA_MOCK_PAYMENTS=True)
class PendingOrderPaymentEntryTests(TestCase):
    def setUp(self):
        self.user = Customer.objects.create_user(
            username="pending_order_owner",
            email="pending-order-owner@example.com",
            password="test-password-for-tests",
        )
        self.product = Product.objects.create(
            name="Pending Order Product",
            slug="pending-order-product",
            is_active=True,
        )
        self.plan = Plan.objects.create(
            product=self.product,
            name="Pending Order Plan",
            slug="pending-order-plan",
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
            idempotency_key="a7f6c3d4-1b2a-4e5f-8c9d-0a1b2c3d4e5f",
        )
        self.client.force_login(self.user)

    def test_orders_page_shows_pay_button_for_pending_order(self):
        response = self.client.get(reverse("portal:orders"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "پرداخت آزمایشی این سفارش")
        self.assertContains(
            response,
            reverse("billing:local_simulator_order_start", args=[self.order.pk]),
        )

    def test_pending_order_can_start_local_simulator(self):
        response = self.client.post(
            reverse("billing:local_simulator_order_start", args=[self.order.pk])
        )
        self.assertEqual(response.status_code, 302)
        attempt = PaymentAttempt.objects.get(order=self.order, provider="local_simulator")
        self.assertIn(str(attempt.pk), response.url)
        self.assertEqual(attempt.status, PaymentAttempt.Status.PENDING)
        self.assertTrue(attempt.provider_reference)

    def test_user_cannot_start_simulation_for_another_users_order(self):
        other = Customer.objects.create_user(
            username="different_pending_order_owner",
            email="different-pending-order-owner@example.com",
            password="test-password-for-tests",
        )
        self.client.force_login(other)
        response = self.client.post(
            reverse("billing:local_simulator_order_start", args=[self.order.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(PaymentAttempt.objects.filter(order=self.order).exists())

    def test_pending_order_payment_entry_is_disabled_when_debug_is_false(self):
        with self.settings(DEBUG=False):
            response = self.client.post(
                reverse("billing:local_simulator_order_start", args=[self.order.pk])
            )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(PaymentAttempt.objects.filter(order=self.order).exists())
