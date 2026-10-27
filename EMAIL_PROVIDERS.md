# Transactional email providers

Nebula Vault uses Django's standard `send_mail` / `EmailMessage` APIs for account verification, password reset and other messages. The provider is selected through environment variables, so application views and Persian email templates do not need provider-specific code.

## Supported providers

| `EMAIL_PROVIDER` | Backend | Credential | Sender variable |
| --- | --- | --- | --- |
| `auto` | Detect configured API key | Resend, then Brevo, then MailerSend; SMTP if configured | Provider-specific |
| `resend` | `accounts.email_backends.ResendEmailBackend` | `RESEND_API_KEY` | `RESEND_FROM_EMAIL` |
| `brevo` | `accounts.email_backends.BrevoEmailBackend` | `BREVO_API_KEY` | `BREVO_FROM_EMAIL` |
| `mailersend` | `accounts.email_backends.MailerSendEmailBackend` | `MAILERSEND_API_KEY` | `MAILERSEND_FROM_EMAIL` |
| `smtp` | Django SMTP backend | `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | `DJANGO_DEFAULT_FROM_EMAIL` |
| `console` | Django console backend | None; development only | Not applicable |

The API backends use HTTPS and Python's standard library, so no extra package is needed. They support text/HTML messages, recipient lists, CC/BCC, reply-to, custom headers where supported, and attachments. The backend returns a successful send count only after the provider accepts the request. Errors are logged and raised unless Django's `fail_silently=True` is used.

## Render setup (Resend test)

1. Set `EMAIL_PROVIDER=resend` and `RESEND_API_KEY` in the Render service's environment.
2. For initial testing, `RESEND_FROM_EMAIL=onboarding@resend.dev` may be used only within Resend's onboarding sender restrictions. It is not a production sender for arbitrary users.
3. Use a recipient address verified/allowed by the Resend account and trigger the site's resend-verification flow. Check Resend Logs and Render logs if it fails.
4. Before sending verification and password-reset emails to arbitrary users, add a domain you control in Resend, publish the DNS records Resend supplies, wait for verification, and set `RESEND_FROM_EMAIL` to a sender on that verified domain (for example `Nebula Vault <noreply@your-domain.example>`).
5. Redeploy/restart the service after environment changes. Do not place API keys in source control, browser code, chat messages, or frontend settings.

## Switching providers

Set exactly one intended provider in `EMAIL_PROVIDER`, then configure its key and sender:
- Resend: `RESEND_API_KEY`, `RESEND_FROM_EMAIL`
- Brevo: `BREVO_API_KEY`, `BREVO_FROM_EMAIL`
- MailerSend: `MAILERSEND_API_KEY`, `MAILERSEND_FROM_EMAIL`

Each provider requires its own account approval and valid sender configuration. A sender/domain accepted by one provider is not automatically verified with another provider. API providers intentionally do not automatically retry the same email through a second provider after a timeout or error: the first provider may have accepted the message before the connection failed, and automatic failover could send duplicate verification/reset messages. Switch provider explicitly through environment configuration instead.

## SMTP and local development

SMTP is available by setting `EMAIL_PROVIDER=smtp` and configuring `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and optionally `DJANGO_DEFAULT_FROM_EMAIL`. Outbound SMTP may be restricted by the hosting provider. For local development, set `EMAIL_PROVIDER=console` to print email contents to the application console.

## Troubleshooting

- `RESEND_API_KEY is not configured` / similar: selected provider's key is missing or empty.
- Sender rejected / validation error: verify the sender address/domain in the provider dashboard and ensure the matching sender environment variable is set.
- HTTP 401/403: verify the correct provider API key, permissions, account status and any IP allowlist.
- HTTP 429: provider rate limit/quota reached.
- HTTP 4xx: check the provider's returned error detail in server logs.
- Network timeout: check that the service can reach the provider's HTTPS API endpoint.
- Do not share API keys in support chats. If a key has been exposed, revoke it and create a replacement.
