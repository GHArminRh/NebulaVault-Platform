import base64
from io import BytesIO

import pyotp
import qrcode


def new_totp_secret():
    return pyotp.random_base32()


def verify_totp(secret, token):
    token = (token or "").replace(" ", "").strip()
    return bool(secret and len(token) == 6 and token.isdigit() and pyotp.TOTP(secret).verify(token, valid_window=1))


def provisioning_uri(secret, username):
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name="Nebula Vault")


def qr_data_uri(uri):
    image = qrcode.make(uri)
    output = BytesIO()
    image.save(output, format="PNG")
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
