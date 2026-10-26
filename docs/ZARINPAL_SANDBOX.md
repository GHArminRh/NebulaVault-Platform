# Zarinpal Sandbox and local payment simulation for Nebula Vault

Nebula Vault supports two different development paths. They are deliberately separate.

## Option A — local simulator (works now without credentials)

Use this when you do not have a domain or Zarinpal merchant ID yet. It does **not** connect to Zarinpal and does not move money; it exercises Nebula Vault's real order, payment-attempt, subscription, and license-finalization services.

In your local server-side `.env` file, set:

```dotenv
DJANGO_DEBUG=True
NEBULA_MOCK_PAYMENTS=True
ZARINPAL_MERCHANT_ID=
ZARINPAL_SANDBOX=True
```

Then sign in, open the pricing page, and choose **«شبیه‌سازی پرداخت محلی»**. On the simulator page, choose either successful or failed payment. Success uses the normal payment-finalization service and activates the test subscription/license; failure leaves the order unpaid and does not activate access. The simulator is only available when both Django DEBUG and NEBULA_MOCK_PAYMENTS are enabled.

Do not expose this mode on a public/production server. Set `DJANGO_DEBUG=False` and `NEBULA_MOCK_PAYMENTS=False` for production.

## Option B — Zarinpal's actual Sandbox

The external Zarinpal Sandbox is a different service. It requires a merchant ID accepted by Zarinpal's test environment, and its callback/registered-domain rules may require a publicly reachable URL. A local simulator cannot prove that Zarinpal's API credentials or callback registration are valid.

Set these values after obtaining a valid Sandbox merchant ID:

- `ZARINPAL_MERCHANT_ID`: test merchant identifier.
- `ZARINPAL_SANDBOX=True`: use the Sandbox API and payment page.
- `ZARINPAL_ENABLED=True`: enable the Zarinpal route.

The Zarinpal route requests a payment authority, saves it against the payment attempt, redirects to the gateway, and verifies the amount server-to-server before finalizing the order. Never grant access based only on the browser's callback parameters.

## Currency

Catalog prices are stored in hundredths of the displayed currency. Zarinpal checkout is available only for plans whose currency is `IRT` (Toman) or `IRR` (Rial); server-side conversion to whole Rials is performed. USD and other currencies are rejected by the actual Zarinpal integration. The local simulator supports any catalog currency because it does not send an amount to a payment provider.

## Tests

Run:

```bash
python manage.py check
python manage.py test billing.test_zarinpal billing.test_local_simulator
```

These automated tests do not perform a live transaction with Zarinpal. Before deployment, also run the existing billing test suite and configure a valid merchant ID and an appropriate callback URL.
