import base64
import hashlib
from io import BytesIO

import pyotp
import qrcode
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def new_totp_secret():
    return pyotp.random_base32()


def _fernet():
    key = base64.urlsafe_b64encode(hashlib.sha256((settings.SECRET_KEY + ':nebula-totp-v1').encode('utf-8')).digest())
    return Fernet(key)


def encrypt_totp_secret(secret):
    return _fernet().encrypt(secret.encode('ascii')).decode('ascii')


def decrypt_totp_secret(secret):
    if not secret:
        return ''
    try:
        return _fernet().decrypt(secret.encode('ascii')).decode('ascii')
    except (InvalidToken, UnicodeError, ValueError):
        return ''


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
