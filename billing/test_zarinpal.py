import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from billing.zarinpal import ZarinpalError, amount_in_rials, request_payment, verify_payment


class ZarinpalAmountTests(SimpleTestCase):
    def test_rial_amount_is_unchanged(self):
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
