# Signed offline license leases

The licensing API can return a device-bound Ed25519 lease in `signed_lease` after successful activation or validation. The lease is capped at 30 days and never extends past the subscription's server-side `expires_at`.

## Configure signing keys

Generate an Ed25519 key pair in a trusted environment, then store only the private seed in the production secret manager. Do not commit either key to the repository.

Example one-time key generation (run in a secure environment, not on the end-user machine):

```python
import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption

key = Ed25519PrivateKey.generate()
private_seed = key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
public_key = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
b64url = lambda b: base64.urlsafe_b64encode(b).decode().rstrip('=')
print('NEBULA_LICENSE_SIGNING_PRIVATE_KEY=' + b64url(private_seed))
print('Desktop license_public_key=' + b64url(public_key))
```

Set `NEBULA_LICENSE_SIGNING_PRIVATE_KEY` in the Django deployment environment. Set the matching public key as `license_public_key` in the desktop app's `license_settings.json` (or `NEBULA_LICENSE_PUBLIC_KEY`). Never put the private seed in the desktop app or public repository.

## Token contract

The compact token is `base64url(payload_json).base64url(signature)`. The Ed25519 signature covers the exact UTF-8 payload bytes. Payload keys are `schema` (1), `license_id`, `device_fingerprint`, `issued_at` and `expires_at`. The client verifies the signature, device binding and lease window. If the signing key is not configured, the server does not mint a lease and the client remains online-only.

## Operational behavior

The client validates online on startup. If unavailable, it can run only while a valid signed lease remains unexpired and no obvious clock rollback is detected. At expiry, online renewal is mandatory and failure to reach the server fails closed. Client-side rollback checks are a tamper signal, not a trusted clock; do not promise protection against a fully compromised endpoint. Revocation cannot take effect on an offline device until it reconnects, so use a maximum 30-day lease and shorten it if faster revocation is required.
