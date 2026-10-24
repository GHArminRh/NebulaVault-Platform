# Email delivery for Nebula Vault

Nebula Vault uses Django SMTP for account verification and password recovery. Gmail credentials are read from the local environment; never put an App Password in Python source, a committed `.env`, screenshots, or chat messages.

## Configure Gmail SMTP

1. Copy `.env.example` to `.env` in the project root if needed.
2. Set `EMAIL_HOST_USER` to the Gmail address you will send mail from.
3. Set `EMAIL_HOST_PASSWORD` to a newly generated Google App Password. Do not use your normal Google account password.
4. Keep `EMAIL_HOST=smtp.gmail.com`, `EMAIL_PORT=587`, and `EMAIL_USE_TLS=True`.
5. Set `DJANGO_DEFAULT_FROM_EMAIL` to the same Gmail address, optionally with a display name.
6. Restart Django so it reloads `.env`.

Example local-only values:

    EMAIL_HOST=smtp.gmail.com
    EMAIL_PORT=587
    EMAIL_USE_TLS=True
    EMAIL_HOST_USER="your-address@gmail.com"
    EMAIL_HOST_PASSWORD="paste-your-new-app-password-here"
    DJANGO_DEFAULT_FROM_EMAIL="Nebula Vault <your-address@gmail.com>"

Do not copy the example values literally. Keep `.env` out of Git; only `.env.example` is committed. In development, if SMTP credentials are absent, Django uses the console backend and prints email messages in the terminal instead of sending them.

## Account flows

- New customer accounts start inactive until the verification link is opened.
- Verification links expire after 24 hours and are invalidated after activation.
- Resending verification is privacy-preserving and limited to five messages per email/IP pair per hour (best effort with the configured Django cache).
- Changing the email in the profile disables the account until the new address is verified.
- Password-reset responses do not disclose whether an account exists. Reset links expire after 24 hours.
- Existing active customers are not automatically disabled by this change.

For production, configure HTTPS, a real shared cache for rate limiting, correct `ALLOWED_HOSTS`, and a sender address/domain aligned with your deployment.