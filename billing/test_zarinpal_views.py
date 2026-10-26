from uuid import uuid4
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Customer
from catalog.models import Plan, Product
from subscriptions.models import Subscription
from .models import PaymentAttempt, PaymentOrder
from .services import create_payment_attempt, create_payment_order


class ZarinPalCallbackViewTests(TestCase):
    def setUp(self):
        self.user = Customer.objects.create_user(
            email="zarinpal-callback@example.test",
            username="zarinpal_callback_user",
            password="test-password",
        )
        self.product = Product.objects.create(
            name="Nebula Vault Gateway Test",
            slug="nebula-vault-gateway-test",
            is_active=True,
        )
        self.plan = Plan.objects.create(
            product=self.product,
            name="Monthly IRR",
            slug="monthly-irr",
            duration_unit=Plan.DurationUnit.MONTHS,
            duration_value=1,
            price_minor_units=25000,
            currency="IRR",
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
            provider="zarinpal",
            idempotency_key=uuid4(),
        )
        self.authority = "A000000000000000000000000000000001"
        self.attempt.provider_authority = self.authority
        self.attempt.status = PaymentAttempt.Status.PENDING
        self.attempt.save(update_fields=["provider_authority", "status", "updated_at"])
        self.callback_url = reverse("billing:zarinpal_callback")

    @patch("billing.views.finalize_payment")
    @patch("billing.views.verify_payment")
    def test_callback_does_not_trust_browser_status_alone(self, verify, finalize):
        response = self.client.get(self.callback_url, {
            "attempt_id": str(self.attempt.pk),
            "Authority": self.authority,
            "Status": "NOK",
        })
        self.assertEqual(response.status_code, 200)
        verify.assert_not_called()
        finalize.assert_not_called()
        self.order.refresh_from_db()
        self.attempt.refresh_from_db()
        self.assertEqual(self.order.status, PaymentOrder.Status.PENDING)
        self.assertEqual(self.attempt.status, PaymentAttempt.Status.PENDING)

    @patch("billing.views.finalize_payment")
    @patch("billing.views.verify_payment")
    def test_success_callback_verifies_saved_amount_then_finalizes(self, verify, finalize):
        verify.return_value = self.authority
        finalize.return_value = self.attempt
        response = self.client.get(self.callback_url, {
            "attempt_id": str(self.attempt.pk),
            "Authority": self.authority,
            "Status": "OK",
            # Untrusted extra callback amount must not be used.
            "amount": "1",
        })
        self.assertEqual(response.status_code, 200)
        verify.assert_called_once_with(
            amount_irr=self.order.amount_minor_units,
            authority=self.authority,
        )
        finalize.assert_called_once_with(
            attempt_id=self.attempt.pk,
            provider_reference=self.authority,
            confirmed_amount_minor_units=self.order.amount_minor_units,
            confirmed_currency="IRR",
        )

    def test_callback_rejects_authority_mismatch(self):
        response = self.client.get(self.callback_url, {
            "attempt_id": str(self.attempt.pk),
            "Authority": "A-different-authority",
            "Status": "OK",
        })
        self.assertEqual(response.status_code, 400)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, PaymentOrder.Status.PENDING)
