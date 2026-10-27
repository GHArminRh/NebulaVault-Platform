"""Provider-neutral Django transactional email backends.

Supported providers:
- Resend HTTPS API
- Brevo transactional email API
- MailerSend Email API
- Django's standard SMTP/console backends (selected in settings)

No provider SDK is required; requests use the Python standard library.
"""
import base64
import json
import logging
import os
from email.utils import parseaddr
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class ProviderEmailBackend(BaseEmailBackend):
    """Shared HTTP, serialization and error handling for email API providers."""

    provider = "provider"
    api_url = ""
    api_key_env = ""
    from_env = ""
    default_from = ""

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.api_key = os.environ.get(self.api_key_env, "").strip()
        self.from_email = os.environ.get(self.from_env, self.default_from).strip()
        self.timeout = max(1, int(os.environ.get("EMAIL_API_TIMEOUT", "15")))

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        if not self.api_key:
            return self._configuration_error(f"{self.api_key_env} is not configured.")
        sent = 0
        for message in email_messages:
            if self._send(message):
                sent += 1
        return sent

    def _configuration_error(self, detail):
        message = f"{self.provider} email backend configuration error: {detail}"
        logger.error(message)
        if not self.fail_silently:
            raise RuntimeError(message)
        return 0

    @staticmethod
    def _address(address):
        name, email = parseaddr(address or "")
        return {"email": email, **({"name": name} if name else {})}

    @staticmethod
    def _addresses(addresses):
        return [ProviderEmailBackend._address(address) for address in (addresses or [])]

    @staticmethod
    def _attachment_data(attachment):
        """Convert Django tuple or MIME attachment to provider-neutral fields."""
        if isinstance(attachment, tuple):
            filename, content = attachment[0], attachment[1]
            mimetype = attachment[2] if len(attachment) > 2 else None
            if isinstance(content, str):
                content = content.encode("utf-8")
            maintype, _, subtype = (mimetype or "application/octet-stream").partition("/")
            return {
                "filename": str(filename or "attachment"),
                "content": base64.b64encode(content).decode("ascii"),
                "content_type": mimetype or "application/octet-stream",
                "disposition": "attachment",
            }

        filename = attachment.get_filename() or "attachment"
        content = attachment.get_payload(decode=True)
        if content is None:
            payload = attachment.get_payload()
            content = payload.encode("utf-8") if isinstance(payload, str) else bytes(payload)
        content_type = attachment.get_content_type()
        content_id = attachment.get("Content-ID")
        return {
            "filename": filename,
            "content": base64.b64encode(content).decode("ascii"),
            "content_type": content_type,
            "disposition": "inline" if content_id else "attachment",
            **({"id": content_id.strip("<>")} if content_id else {}),
        }

    def _common(self, message):
        sender = self._address(message.from_email or self.from_email)
        if not sender.get("email"):
            raise RuntimeError(f"{self.provider} sender email is not configured.")
        html_body = None
        for alternative, mimetype in getattr(message, "alternatives", []) or []:
            if mimetype == "text/html":
                html_body = alternative
        attachments = [
            self._attachment_data(attachment)
            for attachment in (getattr(message, "attachments", None) or [])
        ]
        return {
            "sender": sender,
            "to": self._addresses(message.to),
            "cc": self._addresses(message.cc),
            "bcc": self._addresses(message.bcc),
            "reply_to": self._addresses(message.reply_to),
            "subject": message.subject or "",
            "text": message.body or "",
            "html": html_body,
            "attachments": attachments,
            "headers": dict(getattr(message, "extra_headers", {}) or {}),
        }

    def _payload(self, message):
        raise NotImplementedError

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "NebulaVault-Django-Email/1.0",
        }

    def _send(self, message):
        try:
            payload = self._payload(message)
            request = Request(
                self.api_url,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers=self._headers(),
                method="POST",
            )
            with urlopen(request, timeout=self.timeout) as response:
                status = getattr(response, "status", 200)
                response.read()
                if 200 <= status < 300:
                    return True
                detail = f"HTTP {status}"
        except HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")[:1200]
            detail = f"HTTP {exc.code}: {response_body}"
        except (URLError, TimeoutError, OSError, ValueError, TypeError, RuntimeError) as exc:
            detail = str(exc)[:1200]

        logger.error("%s email delivery failed: %s", self.provider, detail)
        if not self.fail_silently:
            raise RuntimeError(f"{self.provider} email delivery failed: {detail}")
        return False


class ResendEmailBackend(ProviderEmailBackend):
    provider = "Resend"
    api_url = "https://api.resend.com/emails"
    api_key_env = "RESEND_API_KEY"
    from_env = "RESEND_FROM_EMAIL"
    default_from = "onboarding@resend.dev"

    def _headers(self):
        headers = super()._headers()
        headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _payload(self, message):
        data = self._common(message)
        sender = data["sender"]
        payload = {
            "from": f'{sender["name"]} <{sender["email"]}>' if sender.get("name") else sender["email"],
            "to": [item["email"] for item in data["to"]],
            "subject": data["subject"],
            "text": data["text"],
        }
        if data["html"] is not None:
            payload["html"] = data["html"]
        if data["cc"]:
            payload["cc"] = [item["email"] for item in data["cc"]]
        if data["bcc"]:
            payload["bcc"] = [item["email"] for item in data["bcc"]]
        if data["reply_to"]:
            payload["reply_to"] = [item["email"] for item in data["reply_to"]]
        if data["headers"]:
            payload["headers"] = data["headers"]
        if data["attachments"]:
            payload["attachments"] = [
                {"filename": item["filename"], "content": item["content"]}
                for item in data["attachments"]
            ]
        return payload


class BrevoEmailBackend(ProviderEmailBackend):
    provider = "Brevo"
    api_url = "https://api.brevo.com/v3/smtp/email"
    api_key_env = "BREVO_API_KEY"
    from_env = "BREVO_FROM_EMAIL"
    default_from = ""

    def _headers(self):
        headers = super()._headers()
        headers.pop("Authorization", None)
        headers["api-key"] = self.api_key
        return headers

    def _payload(self, message):
        data = self._common(message)
        payload = {
            "sender": data["sender"],
            "to": data["to"],
            "subject": data["subject"],
        }
        # Brevo documents htmlContent and textContent as mutually exclusive
        # body modes for a raw-content request, so prefer HTML when available.
        if data["html"] is not None:
            payload["htmlContent"] = data["html"]
        else:
            payload["textContent"] = data["text"]
        if data["cc"]:
            payload["cc"] = data["cc"]
        if data["bcc"]:
            payload["bcc"] = data["bcc"]
        if data["reply_to"]:
            payload["replyTo"] = data["reply_to"][0]
        if data["headers"]:
            payload["headers"] = data["headers"]
        if data["attachments"]:
            payload["attachment"] = [
                {"name": item["filename"], "content": item["content"]}
                for item in data["attachments"]
            ]
        return payload


class MailerSendEmailBackend(ProviderEmailBackend):
    provider = "MailerSend"
    api_url = "https://api.mailersend.com/v1/email"
    api_key_env = "MAILERSEND_API_KEY"
    from_env = "MAILERSEND_FROM_EMAIL"
    default_from = ""

    def _payload(self, message):
        data = self._common(message)
        payload = {
            "from": data["sender"],
            "to": data["to"],
            "subject": data["subject"],
            "text": data["text"],
        }
        if data["html"] is not None:
            payload["html"] = data["html"]
        if data["cc"]:
            payload["cc"] = data["cc"]
        if data["bcc"]:
            payload["bcc"] = data["bcc"]
        if data["reply_to"]:
            payload["reply_to"] = data["reply_to"][0]
        if data["attachments"]:
            payload["attachments"] = [
                {
                    "filename": item["filename"],
                    "content": item["content"],
                    "disposition": item["disposition"],
                    **({"id": item["id"]} if item.get("id") else {}),
                }
                for item in data["attachments"]
            ]
        if data["headers"]:
            payload["headers"] = data["headers"]
        return payload
