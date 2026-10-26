from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from .zarinpal_gateway import (
    ZarinPalGatewayError,
    request_payment,
    validate_callback_url,
    verify_payment,
)


class ZarinPalGatewayTests(SimpleTestCase):
    def setUp(self):
        self.payments = SimpleNamespace(
            create=Mock(return_value={"data": {"code": 100, "authority": "A000000000000000000000000000000001"}}),
            generate_payment_url=Mock(return_value="https://sandbox.zarinpal.com/pg/StartPay/A000000000000000000000000000000001"),
        )
        self.verifications = SimpleNamespace(
            verify=Mock(return_value={"data": {"code": 100, "ref_id": 123456}})
        )
        self.client = SimpleNamespace(
            payments=self.payments,
            verifications=self.verifications,
        )

    @override_settings(DEBUG=True, ZARINPAL_MERCHANT_ID="test-merchant")
    @patch("billing.zarinpal_gateway._client")
    def test_payment_request_uses_server_amount_and_returns_authority_and_url(self, make_client):
        make_client.return_value = self.client
        authority, url = request_payment(
            amount_irr=25000,
            callback_url="https://example.test/billing/zarinpal/callback/?attempt_id=abc",
            description="Nebula Vault Monthly",
            email="customer@example.test",
        )
        self.assertEqual(authority, "A000000000000000000000000000000001")
        self.assertTrue(url.startswith("https://"))
        self.payments.create.assert_called_once()
        payload = self.payments.create.call_args.args[0]
        self.assertEqual(payload["amount"], 25000)
        self.assertEqual(payload["metadata"]["email"], "customer@example.test")

    @override_settings(DEBUG=True, ZARINPAL_MERCHANT_ID="test-merchant")
    @patch("billing.zarinpal_gateway._client")
    def test_payment_request_rejects_non_success_code(self, make_client):
        self.payments.create.return_value = {"data": {"code":  -9, "message": "failed"}}
        make_client.return_value = self.client
        with self.assertRaises(ZarinPalGatewayError):
            request_payment(
                amount_irr=25000,
                callback_url="https://example.test/callback/",
                description="Nebula Vault Monthly",
            )

    def test_payment_request_rejects_amount_below_minimum(self):
        with self.assertRaises(ZarinPalGatewayError):
            request_payment(
                amount_irr=999,
                callback_url="https://example.test/callback/",
                description="Test",
            )

    @override_settings(DEBUG=False)
    def test_production_callback_must_use_https(self):
        with self.assertRaises(ZarinPalGatewayError):
            validate_callback_url("http://example.test/callback/")

    @override_settings(DEBUG=False)
    def test_production_callback_accepts_https(self):
        self.assertEqual(
            validate_callback_url("https://example.test/callback/"),
            "https://example.test/callback/",
        )

    @override_settings(ZARINPAL_MERCHANT_ID="test-merchant")
    @patch("billing.zarinpal_gateway._client")
    def test_verification_uses_the_authority_and_accepts_verified_code(self, make_client):
        make_client.return_value = self.client
        reference = verify_payment(
            amount_irr=25000,
            authority="A000000000000000000000000000000001",
        )
        self.assertEqual(reference, "A000000000000000000000000000000001")
        self.verifications.verify.assert_called_once_with({
            "amount": 25000,
            "authority": "A000000000000000000000000000000001",
        })

    @override_settings(ZARINPAL_MERCHANT_ID="test-merchant")
    @patch("billing.zarinpal_gateway._client")
    def test_verification_accepts_already_verified_code_for_safe_retries(self, make_client):
        self.verifications.verify.return_value = {"data": {"code": 101}}
        make_client.return_value = self.client
        self.assertEqual(
            verify_payment(amount_irr=1000, authority="A000000000000000000000000000000001"),
            "A000000000000000000000000000000001",
        )

    @override_settings(ZARINPAL_MERCHANT_ID="test-merchant")
    @patch("billing.zarinpal_gateway._client")
    def test_verification_does_not_accept_unverified_codes(self, make_client):
        self.verifications.verify.return_value = {"data": {"code":  -21}}
        make_client.return_value = self.client
        with self.assertRaises(ZarinPalGatewayError):
            verify_payment(amount_irr=1000, authority="A000000000000000000000000000000001")
