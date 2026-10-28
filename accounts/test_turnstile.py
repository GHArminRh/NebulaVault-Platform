import json
from unittest.mock import MagicMock, patch

from django.test import TestCase, SimpleTestCase, override_settings

from accounts.forms import RegisterForm
from accounts.turnstile import verify_turnstile


class TurnstileVerificationTests(TestCase):
    def test_missing_token_or_secret_fails_without_network_request(self):
        with patch("accounts.turnstile.urlopen") as urlopen:
            self.assertFalse(verify_turnstile("", secret_key="secret", verify_url="https://verify.example"))
            self.assertFalse(verify_turnstile("token", secret_key="", verify_url="https://verify.example"))
            urlopen.assert_not_called()

    @patch("accounts.turnstile.urlopen")
    def test_successful_siteverify_response_is_accepted(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps({"success": True}).encode()
        urlopen.return_value = response

        self.assertTrue(verify_turnstile(
            "valid-token", secret_key="secret", verify_url="https://verify.example"
        ))
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertIn(b"response=valid-token", request.data)
        self.assertIn(b"secret=secret", request.data)

    @patch("accounts.turnstile.urlopen")
    def test_unsuccessful_or_unavailable_siteverify_fails_closed(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps({"success": False}).encode()
        urlopen.return_value = response
        self.assertFalse(verify_turnstile(
            "invalid-token", secret_key="secret", verify_url="https://verify.example"
        ))

        urlopen.side_effect = TimeoutError("provider timeout")
        self.assertFalse(verify_turnstile(
            "token", secret_key="secret", verify_url="https://verify.example"
        ))

    @override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SECRET_KEY="secret")
    @patch("accounts.forms.verify_turnstile", return_value=False)
    def test_registration_rejects_missing_or_invalid_turnstile(self, verify):
        form = RegisterForm(data={
            "email": "captcha-test@example.com",
            "password1": "Secure-registration-password-2026!",
            "password2": "Secure-registration-password-2026!",
        })
        self.assertFalse(form.is_valid())
        self.assertTrue(any("تأیید امنیتی" in error for error in form.non_field_errors()))
        verify.assert_called_once()
