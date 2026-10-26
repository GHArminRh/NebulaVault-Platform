# Signed offline license leases

The licensing API returns a device-bound Ed25519 lease in `signed_lease` after successful activation or validation when the server signing key is configured. The lease expires at the subscription's authoritative server-side `expires_at` timestamp, so it follows the complete purchased term (for example, two months or one year) and never outlives it.

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

Set `NEBULA_LICENSE_SIGNING_PRIVATE_KEY` in the Django deployment environment/secret manager. The matching public key is pinned into the corresponding desktop release and is not read from mutable client settings. Never put the private seed in the desktop app, source repository, logs, or customer package. Rotating the signing key requires a matching desktop release with the new public-key pin.

## Token contract

The compact token is `base64url(payload_json).base64url(signature)`. The Ed25519 signature covers the exact UTF-8 payload bytes. Payload keys are `schema` (1), `license_id`, `device_fingerprint`, `issued_at` and `expires_at`. The client verifies the signature, device binding, license identity, and that the lease expiry exactly matches the subscription expiry returned by the server. If the signing key is not configured, the server does not mint a lease; online use can continue, but offline fallback is unavailable.

## Operational behavior

The desktop validates online at startup and its local engine rechecks the server every 30 seconds while running. The frontend reflects the backend's cached status and opens the existing license gate after a definitive rejection. A revoked/expired/deactivated key and its offline lease are cleared on that rejection so a later network failure cannot reactivate the rejected lease. When the server cannot be reached, use is allowed only while the signed lease remains unexpired and no obvious clock rollback is detected. At subscription expiry, online renewal/activation is mandatory. Revocation cannot take effect on a truly offline device until it reconnects; with a full-term lease, that delay may last until the purchased term ends. Client-side rollback checks are a tamper signal, not a trusted clock, and cannot guarantee resistance to a fully compromised or patched endpoint.
