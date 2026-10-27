import json
import os
from unittest.mock import MagicMock, patch

from django.core.mail import EmailMultiAlternatives
from django.test import SimpleTestCase

from accounts.email_backends import ResendEmailBackend


class ResendEmailBackendTests(SimpleTestCase):
    def make_message(self):
        message = EmailMultiAlternatives(
            subject="تأیید حساب",
            body="کد شما 123456 است",
            from_email="Nebula Vault <sender@example.com>",
            to=["User One <user@example.com>"],
            cc=["copy@example.com"],
            bcc=["hidden@example.com"],
            reply_to=["support@example.com"],
            headers={"X-Nebula-Test": "yes"},
        )
        message.attach_alternative("<p>کد شما <b>123456</b> است</p>", "text/html")
        message.attach("info.txt", "attachment text", "text/plain")
        return message

    def backend(self, env):
        with patch.dict(os.environ, env, clear=False):
            return ResendEmailBackend()

    def test_payload_supports_html_recipients_headers_and_attachments(self):
        backend = self.backend({"RESEND_API_KEY": "test-key"})
        payload = backend._payload(self.make_message())
        self.assertEqual(payload["from"], "Nebula Vault <sender@example.com>")
        self.assertEqual(payload["to"], ["user@example.com"])
        self.assertEqual(payload["cc"], ["copy@example.com"])
        self.assertEqual(payload["bcc"], ["hidden@example.com"])
        self.assertEqual(payload["reply_to"], ["support@example.com"])
        self.assertIn("html", payload)
        self.assertEqual(payload["attachments"][0]["filename"], "info.txt")
        self.assertEqual(payload["headers"]["X-Nebula-Test"], "yes")

    @patch("accounts.email_backends.urlopen")
    def test_send_uses_https_and_returns_success_count(self, urlopen):
        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        urlopen.return_value = response
        backend = self.backend({"RESEND_API_KEY": "test-key"})
        self.assertEqual(backend.send_messages([self.make_message()]), 1)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.resend.com/emails")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        self.assertEqual(
            json.loads(request.data.decode("utf-8"))["subject"], "تأیید حساب"
        )

    def test_missing_api_key_fails_clearly(self):
        with patch.dict(os.environ, {"RESEND_API_KEY": ""}, clear=False):
            backend = ResendEmailBackend()
        with self.assertRaisesRegex(RuntimeError, "RESEND_API_KEY"):
            backend.send_messages([self.make_message()])

    def test_fail_silently_returns_zero_when_key_is_missing(self):
        with patch.dict(os.environ, {"RESEND_API_KEY": ""}, clear=False):
            backend = ResendEmailBackend(fail_silently=True)
        self.assertEqual(backend.send_messages([self.make_message()]), 0)
