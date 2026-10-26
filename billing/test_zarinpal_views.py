from uuid import uuid4
from unittest.mock import patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware

from accounts.models import Customer
from catalog.models import Plan, Product
from .models import PaymentAttempt, PaymentOrder
from .services import create_payment_attempt, create_payment_order
from .views import zarinpal_start


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
        self.attempt.provider_reference = self.authority
        self.attempt.status = PaymentAttempt.Status.PENDING
        self.attempt.save(update_fields=["provider_reference", "status", "updated_at"])
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

    @override_settings(
        ZARINPAL_ENABLED=True,
        ZARINPAL_MERCHANT_ID="test-merchant",
        NEBULA_MOCK_PAYMENTS=False,
        DEBUG=True,
    )
    @patch("billing.views.request_payment")
    @patch("billing.views._existing_payment_url")
    def test_start_reuses_pending_attempt_instead_of_creating_duplicate(
        self, existing_url, request_payment_mock
    ):
        existing_url.return_value = (
            "https://sandbox.zarinpal.com/pg/StartPay/" + self.authority
        )
        factory = RequestFactory()
        request = factory.post(
            reverse("billing:zarinpal_start", kwargs={"order_id": self.order.pk}),
            {"request_key": str(uuid4())},
        )
        request.user = self.user
        SessionMiddleware(lambda req: None).process_request(request)
        request._messages = FallbackStorage(request)

        response = zarinpal_start(request, order_id=self.order.pk)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], existing_url.return_value)
        request_payment_mock.assert_not_called()
        self.assertEqual(
            PaymentAttempt.objects.filter(order=self.order, provider="zarinpal").count(),
            1,
        )
