import json
import os
from unittest.mock import MagicMock, patch

from django.core.mail import EmailMultiAlternatives
from django.test import SimpleTestCase

from accounts.email_backends import (
    BrevoEmailBackend,
    MailerSendEmailBackend,
    ResendEmailBackend,
)


class ProviderEmailBackendTests(SimpleTestCase):
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

    def backend(self, backend_class, env):
        with patch.dict(os.environ, env, clear=False):
            return backend_class()

    def test_resend_payload_and_attachment(self):
        backend = self.backend(ResendEmailBackend, {"RESEND_API_KEY": "test-key"})
        payload = backend._payload(self.make_message())
        self.assertEqual(payload["from"], "Nebula Vault <sender@example.com>")
        self.assertEqual(payload["to"], ["user@example.com"])
        self.assertEqual(payload["cc"], ["copy@example.com"])
        self.assertEqual(payload["bcc"], ["hidden@example.com"])
        self.assertEqual(payload["reply_to"], ["support@example.com"])
        self.assertIn("html", payload)
        self.assertEqual(payload["attachments"][0]["filename"], "info.txt")
        self.assertEqual(payload["headers"]["X-Nebula-Test"], "yes")

    def test_brevo_payload_uses_api_key_header_and_verified_sender_setting(self):
        backend = self.backend(
            BrevoEmailBackend,
            {"BREVO_API_KEY": "test-key", "BREVO_FROM_EMAIL": "sender@example.com"},
        )
        payload = backend._payload(self.make_message())
        self.assertEqual(payload["sender"]["email"], "sender@example.com")
        self.assertEqual(payload["to"][0]["email"], "user@example.com")
        self.assertEqual(payload["replyTo"]["email"], "support@example.com")
        self.assertEqual(payload["attachment"][0]["name"], "info.txt")
        headers = backend._headers()
        self.assertEqual(headers["api-key"], "test-key")
        self.assertNotIn("Authorization", headers)

    def test_mailersend_payload_contains_expected_shape(self):
        backend = self.backend(
            MailerSendEmailBackend,
            {"MAILERSEND_API_KEY": "test-key", "MAILERSEND_FROM_EMAIL": "sender@example.com"},
        )
        payload = backend._payload(self.make_message())
        self.assertEqual(payload["from"]["email"], "sender@example.com")
        self.assertEqual(payload["to"][0]["email"], "user@example.com")
        self.assertEqual(payload["reply_to"]["email"], "support@example.com")
        self.assertEqual(payload["attachments"][0]["filename"], "info.txt")

    @patch("accounts.email_backends.urlopen")
    def test_resend_send_uses_https_and_returns_success_count(self, urlopen):
        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        urlopen.return_value = response
        backend = self.backend(ResendEmailBackend, {"RESEND_API_KEY": "test-key"})
        self.assertEqual(backend.send_messages([self.make_message()]), 1)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.resend.com/emails")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        self.assertEqual(json.loads(request.data.decode("utf-8"))["subject"], "تأیید حساب")

    def test_missing_api_key_fails_clearly(self):
        with patch.dict(os.environ, {"RESEND_API_KEY": ""}, clear=False):
            backend = ResendEmailBackend()
        with self.assertRaisesRegex(RuntimeError, "RESEND_API_KEY"):
            backend.send_messages([self.make_message()])
