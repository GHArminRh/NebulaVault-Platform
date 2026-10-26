import base64
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from django.test import SimpleTestCase

from .views import _sign_offline_lease


def _b64url(value):
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


class SignedOfflineLeaseTests(SimpleTestCase):
    def setUp(self):
        self.private_key = Ed25519PrivateKey.generate()
        seed = self.private_key.private_bytes_raw()
        self.public_key = self.private_key.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )
        self.env = patch.dict(
            "os.environ",
            {"NEBULA_LICENSE_SIGNING_PRIVATE_KEY": _b64url(seed)},
        )
        self.env.start()
        self.addCleanup(self.env.stop)

    def _license(self, expires_at):
        return SimpleNamespace(
            pk="license-123",
            subscription=SimpleNamespace(expires_at=expires_at),
        )

    def test_lease_is_signed_and_bound_to_device(self):
        now = datetime.now(timezone.utc)
        subscription_end = now + timedelta(days=90)
        with patch("licensing.views.time.time", return_value=now.timestamp()):
            token = _sign_offline_lease(
                self._license(subscription_end), "device-xyz"
            )
        self.assertIsNotNone(token)
        payload_part, signature_part = token.split(".")
        payload_bytes = base64.urlsafe_b64decode(
            payload_part + "=" * (-len(payload_part) % 4)
        )
        signature = base64.urlsafe_b64decode(
            signature_part + "=" * (-len(signature_part) % 4)
        )
        self.private_key.public_key().verify(signature, payload_bytes)
        payload = json.loads(payload_bytes)
        self.assertEqual(payload["license_id"], "license-123")
        self.assertEqual(payload["device_fingerprint"], "device-xyz")
        self.assertEqual(payload["expires_at"], int(subscription_end.timestamp()))
        self.assertGreater(payload["expires_at"] - payload["issued_at"], 30 * 24 * 60 * 60)

    def test_lease_never_outlives_subscription(self):
        now = datetime.now(timezone.utc)
        subscription_end = now + timedelta(days=2)
        with patch("licensing.views.time.time", return_value=now.timestamp()):
            token = _sign_offline_lease(self._license(subscription_end), "device-xyz")
        payload_part = token.split(".")[0]
        payload = json.loads(
            base64.urlsafe_b64decode(
                payload_part + "=" * (-len(payload_part) % 4)
            )
        )
        self.assertEqual(payload["expires_at"], int(subscription_end.timestamp()))

    def test_expired_subscription_gets_no_lease(self):
        now = datetime.now(timezone.utc)
        with patch("licensing.views.time.time", return_value=now.timestamp()):
            token = _sign_offline_lease(
                self._license(now - timedelta(seconds=1)), "device-xyz"
            )
        self.assertIsNone(token)

    def test_missing_private_key_fails_closed(self):
        with patch.dict("os.environ", {"NEBULA_LICENSE_SIGNING_PRIVATE_KEY": ""}):
            token = _sign_offline_lease(
                self._license(datetime.now(timezone.utc) + timedelta(days=5)),
                "device-xyz",
            )
        self.assertIsNone(token)
