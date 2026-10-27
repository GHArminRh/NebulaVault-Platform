"""Transactional email backend using the Resend HTTPS API.

This avoids SMTP connectivity restrictions on hosts such as Render. The default
Resend onboarding sender is intended only for initial testing; verify a domain
before sending to arbitrary recipients.
"""
import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    """Send Django EmailMessage objects through Resend's REST API."""

    api_url = "https://api.resend.com/emails"

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.api_key = os.environ.get("RESEND_API_KEY", "").strip()
        self.from_email = os.environ.get(
            "RESEND_FROM_EMAIL", "onboarding@resend.dev"
        ).strip()
        self.timeout = int(os.environ.get("RESEND_TIMEOUT", "15"))

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        if not self.api_key:
            if self.fail_silently:
                logger.error("Resend email backend selected but RESEND_API_KEY is missing.")
                return 0
            raise RuntimeError("RESEND_API_KEY is not configured.")

        sent = 0
        for message in email_messages:
            if self._send(message):
                sent += 1
        return sent

    def _send(self, message):
        recipients = list(dict.fromkeys(
            list(message.to or []) + list(message.cc or []) + list(message.bcc or [])
        ))
        if not recipients:
            return False

        payload = {
            "from": self.from_email,
            "to": recipients,
            "subject": message.subject or "",
            "text": message.body or "",
        }
        html_body = None
        for alternative, mimetype in getattr(message, "alternatives", []) or []:
            if mimetype == "text/html":
                html_body = alternative
        if html_body is not None:
            payload["html"] = html_body
        if message.reply_to:
            payload["reply_to"] = message.reply_to

        # Resend expects file contents to be explicitly encoded. Do not silently
        # drop attachments if a future email starts using them.
        if getattr(message, "attachments", None):
            raise NotImplementedError(
                "ResendEmailBackend attachment support has not been configured."
            )

        request = Request(
            self.api_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "NebulaVault-Django/1.0",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                status = getattr(response, "status", 200)
                response.read()
                if 200 <= status < 300:
                    return True
                error = f"Resend API returned HTTP {status}"
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            error = f"Resend API returned HTTP {exc.code}: {detail}"
        except (URLError, TimeoutError, OSError) as exc:
            error = f"Could not reach Resend API: {exc}"

        logger.error("Email delivery through Resend failed: %s", error)
        if not self.fail_silently:
            raise RuntimeError(error)
        return False
