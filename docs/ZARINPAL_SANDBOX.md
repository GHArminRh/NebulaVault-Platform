# Zarinpal Sandbox for Nebula Vault

This branch integrates Zarinpal API v4. Sandbox mode defaults to enabled and does not process real payments.

## Environment configuration

Set these values in the server-side `.env` file:

- `ZARINPAL_MERCHANT_ID`: merchant identifier for the Zarinpal test environment.
- `ZARINPAL_SANDBOX=True`: use sandbox API and payment page.
- `ZARINPAL_ENABLED=True`: enable the payment routes.

Do not commit merchant credentials. The callback URL must be publicly reachable over HTTPS; localhost is not suitable for a real gateway callback.

## Currency

Catalog prices are stored in hundredths of the currency. Zarinpal checkout is available only for plans whose currency is `IRT` (Toman) or `IRR` (Rial); server-side conversion to whole Rials is performed. USD and other currencies are intentionally rejected by this gateway.

## Payment flow

1. An authenticated customer chooses Zarinpal checkout on the pricing page.
2. The server creates/reuses a pending order, creates a payment attempt, requests an authority, and saves it.
3. The customer is redirected to the Zarinpal sandbox payment page.
4. The callback locates the saved authority and verifies the exact amount with Zarinpal server-to-server.
5. Only after successful verification does the existing `finalize_payment` service mark the order paid and activate subscription/license access.

## Tests

Run `python manage.py test billing.test_zarinpal` from the project root. These unit tests mock HTTP calls and do not perform a live Sandbox transaction. Before deployment, also run the existing billing tests and Django checks, and configure a public HTTPS callback URL.