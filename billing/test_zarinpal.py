import json
import urllib.error
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from billing.zarinpal import ZarinpalError, amount_in_rials, request_payment, verify_payment


class ZarinpalAmountTests(SimpleTestCase):
    def test_rial_minor_units_convert_to_whole_rials(self):
        self.assertEqual(amount_in_rials(120000, "IRR"), 1200)

    def test_toman_amount_is_converted_to_rials(self):
        self.assertEqual(amount_in_rials(12000, "IRT"), 1200)

    def test_other_currency_is_rejected(self):
        with self.assertRaises(ZarinpalError):
            amount_in_rials(12000, "USD")


@override_settings(ZARINPAL_MERCHANT_ID="sandbox-merchant", ZARINPAL_SANDBOX=True)
class ZarinpalApiTests(SimpleTestCase):
    @patch("billing.zarinpal.urllib.request.urlopen")
    def test_request_uses_sandbox_and_returns_start_url(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            "data": {"code": 100, "authority": "A123"}, "errors": []
        }).encode()
        urlopen.return_value = response
        authority, url = request_payment(
            amount=100000, description="Test order",
            callback_url="https://example.test/billing/zarinpal/callback/",
        )
        self.assertEqual(authority, "A123")
        self.assertEqual(url, "https://sandbox.zarinpal.com/pg/StartPay/A123")
        request = urlopen.call_args.args[0]
        self.assertTrue(request.full_url.startswith("https://sandbox.zarinpal.com/pg/v4/payment/request.json"))

    @patch("billing.zarinpal.urllib.request.urlopen")
    def test_http_error_logs_gateway_validation_details_without_sensitive_values(self, urlopen):
        response_body = json.dumps({
            "errors": {"code": "INVALID_CALLBACK", "message": "Invalid callback URL https://private.example/cb?token=secret for buyer@example.test"}
        }).encode()
        urlopen.side_effect = urllib.error.HTTPError(
            "https://sandbox.zarinpal.com/pg/v4/payment/request.json",
            422, "Unprocessable Entity", {}, __import__("io").BytesIO(response_body),
        )
        with self.assertLogs("billing.zarinpal", level="WARNING") as captured:
            with self.assertRaisesRegex(ZarinpalError, "HTTP 422"):
                request_payment(
                    amount=100000, description="Test order",
                    callback_url="https://private.example/cb?token=secret",
                )
        log_text = "\n".join(captured.output)
        self.assertIn("INVALID_CALLBACK", log_text)
        self.assertIn("[url]", log_text)
        self.assertIn("[email]", log_text)
        self.assertNotIn("secret", log_text)
        self.assertNotIn("buyer@example.test", log_text)

    @patch("billing.zarinpal.urllib.request.urlopen")
    def test_verify_accepts_success_code_and_returns_reference(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            "data": {"code": 100, "ref_id": 987654}, "errors": []
        }).encode()
        urlopen.return_value = response
        result = verify_payment(authority="A123", amount=100000)
        self.assertEqual(result["ref_id"], "987654")

    @patch("billing.zarinpal.urllib.request.urlopen")
    def test_verify_rejects_unverified_payment(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            "data": {"code": -9}, "errors": []
        }).encode()
        urlopen.return_value = response
        with self.assertRaises(ZarinpalError):
            verify_payment(authority="A123", amount=100000)


class ZarinpalLiveModeTests(SimpleTestCase):
    @override_settings(
        ZARINPAL_MERCHANT_ID="merchant-test",
        ZARINPAL_SANDBOX=False,
    )
    @patch("billing.zarinpal.urllib.request.urlopen")
    def test_live_request_uses_production_endpoint(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            "data": {"code": 100, "authority": "LIVE123"}, "errors": []
        }).encode()
        urlopen.return_value = response

        authority, url = request_payment(
            amount=1200,
            description="Live order",
            callback_url="https://example.test/billing/zarinpal/callback/",
            email="buyer@example.test",
        )

        self.assertEqual(authority, "LIVE123")
        self.assertEqual(url, "https://www.zarinpal.com/pg/StartPay/LIVE123")
        request = urlopen.call_args.args[0]
        self.assertTrue(request.full_url.startswith(
            "https://payment.zarinpal.com/pg/v4/payment/request.json"
        ))
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["merchant_id"], "merchant-test")
        self.assertEqual(payload["amount"], 1200)
        self.assertEqual(payload["metadata"]["email"], "buyer@example.test")

    @override_settings(ZARINPAL_MERCHANT_ID="sandbox-merchant", ZARINPAL_SANDBOX=True)
    @patch("billing.zarinpal.urllib.request.urlopen")
    def test_verify_accepts_already_verified_callback(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            "data": {"code": 101, "ref_id": 987654}, "errors": []
        }).encode()
        urlopen.return_value = response

        result = verify_payment(authority="A123", amount=100000)

        self.assertEqual(result["code"], 101)
        self.assertEqual(result["ref_id"], "987654")

    @override_settings(ZARINPAL_MERCHANT_ID="", ZARINPAL_SANDBOX=False)
    def test_request_fails_clearly_when_merchant_id_is_missing(self):
        with self.assertRaisesRegex(ZarinpalError, "شناسه پذیرنده"):
            request_payment(
                amount=1200,
                description="Order",
                callback_url="https://example.test/callback/",
            )

    def test_inexact_currency_amounts_are_rejected(self):
        with self.assertRaises(ZarinpalError):
            amount_in_rials(120001, "IRR")
        with self.assertRaises(ZarinpalError):
            amount_in_rials(12001, "IRT")
