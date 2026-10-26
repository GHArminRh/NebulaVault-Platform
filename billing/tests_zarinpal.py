from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from .zarinpal import ZarinpalError, request_payment, verify_payment


@override_settings(ZARINPAL_MERCHANT_ID="test-merchant", ZARINPAL_SANDBOX=True)
class ZarinpalAdapterTests(SimpleTestCase):
    @patch("billing.zarinpal._post")
    def test_request_returns_authority_and_sandbox_url(self, post):
        post.return_value = {"data": {"code": 100, "authority": "A0000000000000000000000000000000001"}}
        authority, url = request_payment(
            amount_rial=10000,
            description="test order",
            callback_url="https://example.test/callback",
            email="buyer@example.test",
        )
        self.assertEqual(authority, "A0000000000000000000000000000000001")
        self.assertIn("sandbox.zarinpal.com/pg/StartPay/", url)
        self.assertEqual(post.call_args.args[1]["amount"], 10000)

    @patch("billing.zarinpal._post")
    def test_verify_requires_reference_id(self, post):
        post.return_value = {"data": {"code": 100, "ref_id": 12345}}
        self.assertEqual(
            verify_payment(amount_rial=10000, authority="A-test"),
            (True, "12345", "پرداخت تأیید شد."),
        )

    @patch("billing.zarinpal._post")
    def test_request_rejects_small_amount(self, post):
        with self.assertRaises(ZarinpalError):
            request_payment(
                amount_rial=999,
                description="test",
                callback_url="https://example.test/callback",
            )
        post.assert_not_called()
