# Resend transactional email

Nebula Vault continues to use Django's standard `send_mail` and `EmailMessage` APIs for account verification, password reset and other messages. The custom backend sends messages to Resend over HTTPS, so outbound SMTP access and an extra Python package are not required.

## Configuration

Set these variables on the Render web service:

- `RESEND_API_KEY`: secret API key from Resend. Keep it only in server-side environment settings.
- `RESEND_FROM_EMAIL`: use `onboarding@resend.dev` only for restricted initial testing, or use an address on a domain verified in Resend.
- `EMAIL_API_TIMEOUT`: optional timeout in seconds (default 15).

When `RESEND_API_KEY` is present, Django selects `accounts.email_backends.ResendEmailBackend` automatically and prioritizes `RESEND_FROM_EMAIL` over a legacy Gmail sender setting. If the key is absent, existing SMTP/console fallback behavior remains. `DJANGO_EMAIL_BACKEND` remains available as an explicit legacy override.

## First live test

1. In Render, open the `nebula-vault` service and confirm `RESEND_API_KEY` is configured. Do not put the key in source control or chat.
2. Set `RESEND_FROM_EMAIL=onboarding@resend.dev` for initial testing if the Resend account permits it.
3. Redeploy/restart the service and use the account verification resend flow with a recipient Resend allows for the onboarding sender.
4. Check Resend email logs and Render service logs for the API result.

Important: `onboarding@resend.dev` is a restricted testing sender and is not suitable for sending public signup or password-reset messages to arbitrary users. For production, add a domain you control to Resend, publish the DNS records Resend provides, wait until the domain is verified, then set `RESEND_FROM_EMAIL` to an address on that domain. The Render-provided `onrender.com` subdomain is not a domain you control for this purpose.

## Features and troubleshooting

The backend supports text and HTML alternatives, recipients, CC/BCC, reply-to, custom headers and attachments. It reports success only when Resend accepts a request. HTTP and network errors are logged and raised unless Django uses `fail_silently=True`. It does not automatically retry after errors because a timeout may occur after the provider has accepted a message, which could create duplicates.

- HTTP 401/403: check the API key and account permissions.
- Sender/domain error: verify the sender and domain in Resend and check `RESEND_FROM_EMAIL`.
- Recipient restriction: the onboarding sender is limited; verify a domain for public delivery.
- HTTP 429: check account quota/rate limits.
- No email in inbox: inspect Resend and Render logs; API acceptance does not guarantee inbox delivery.
