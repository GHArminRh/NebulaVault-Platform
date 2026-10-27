"""Django email backend for the Resend transactional email HTTPS API."""
import base64
import json
import logging
import os
from email.utils import parseaddr
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    """Deliver Django EmailMessage objects through Resend without extra packages."""

    api_url = "https://api.resend.com/emails"

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.api_key = os.environ.get("RESEND_API_KEY", "").strip()
        self.from_email = os.environ.get(
            "RESEND_FROM_EMAIL", "onboarding@resend.dev"
        ).strip()
        self.timeout = max(1, int(os.environ.get("EMAIL_API_TIMEOUT", "15")))

    @staticmethod
    def _email(address):
        name, email = parseaddr(address or "")
        return {"email": email, **({"name": name} if name else {})}

    @staticmethod
    def _attachment(attachment):
        if isinstance(attachment, tuple):
            filename, content = attachment[0], attachment[1]
            if isinstance(content, str):
                content = content.encode("utf-8")
            return {
                "filename": str(filename or "attachment"),
                "content": base64.b64encode(content).decode("ascii"),
            }
        filename = attachment.get_filename() or "attachment"
        content = attachment.get_payload(decode=True)
        if content is None:
            content = attachment.get_payload()
            if isinstance(content, str):
                content = content.encode("utf-8")
        return {
            "filename": filename,
            "content": base64.b64encode(content).decode("ascii"),
        }

    def _payload(self, message):
        sender = (message.from_email or self.from_email).strip()
        if not sender:
            raise RuntimeError("RESEND_FROM_EMAIL is not configured.")

        payload = {
            "from": sender,
            "to": [self._email(item)["email"] for item in (message.to or [])],
            "subject": message.subject or "",
            "text": message.body or "",
        }
        html_body = next(
            (
                content
                for content, mimetype in (getattr(message, "alternatives", None) or [])
                if mimetype == "text/html"
            ),
            None,
        )
        if html_body is not None:
            payload["html"] = html_body
        if message.cc:
            payload["cc"] = [self._email(item)["email"] for item in message.cc]
        if message.bcc:
            payload["bcc"] = [self._email(item)["email"] for item in message.bcc]
        if message.reply_to:
            payload["reply_to"] = [
                self._email(item)["email"] for item in message.reply_to
            ]
        if getattr(message, "extra_headers", None):
            payload["headers"] = message.extra_headers
        attachments = [
            self._attachment(item)
            for item in (getattr(message, "attachments", None) or [])
        ]
        if attachments:
            payload["attachments"] = attachments
        if not payload["to"]:
            raise RuntimeError("Resend email requires at least one recipient.")
        return payload

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        if not self.api_key:
            error = "RESEND_API_KEY is not configured."
            logger.error(error)
            if not self.fail_silently:
                raise RuntimeError(error)
            return 0

        sent = 0
        for message in email_messages:
            try:
                body = json.dumps(
                    self._payload(message), ensure_ascii=False
                ).encode("utf-8")
                request = Request(
                    self.api_url,
                    data=body,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "User-Agent": "NebulaVault-Django-Email/1.0",
                    },
                    method="POST",
                )
                with urlopen(request, timeout=self.timeout) as response:
                    status = getattr(response, "status", 200)
                    response.read()
                if 200 <= status < 300:
                    sent += 1
                else:
                    raise RuntimeError(f"Resend returned HTTP {status}.")
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:1000]
                error = f"Resend returned HTTP {exc.code}: {detail}"
                logger.error("%s", error)
                if not self.fail_silently:
                    raise RuntimeError(error) from exc
            except (URLError, TimeoutError, OSError, ValueError, TypeError, RuntimeError) as exc:
                logger.error("Resend email delivery failed: %s", str(exc)[:1000])
                if not self.fail_silently:
                    raise RuntimeError(f"Resend email delivery failed: {exc}") from exc
        return sent
