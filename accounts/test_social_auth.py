"""Regression tests for customer Google OAuth entry points."""

from unittest.mock import patch

from django.http import HttpResponseRedirect
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(
    SOCIAL_AUTH_GOOGLE_ENABLED=True,
    SOCIAL_AUTH_APPLE_ENABLED=False,
    TURNSTILE_ENABLED=False,
    SITE_BASE_URL="https://mydigigi.ir",
)
class CustomerGoogleOAuthTests(TestCase):
    def test_login_and_registration_pages_render_google_actions(self):
        login_response = self.client.get(reverse("login"))
        self.assertEqual(login_response.status_code, 200)
        self.assertContains(login_response, "ادامه با Google")

        register_response = self.client.get(reverse("accounts:register"))
        self.assertEqual(register_response.status_code, 200)
        self.assertContains(register_response, "ثبت‌نام با Google")

    def test_google_start_requires_post(self):
        response = self.client.get(
            reverse(
                "accounts:social_start",
                kwargs={"provider": "google", "flow": "login"},
            )
        )
        self.assertEqual(response.status_code, 405)

    def test_registration_oauth_requires_terms_acceptance(self):
        with patch("accounts.social_views.get_oauth_client") as get_client:
            response = self.client.post(
                reverse(
                    "accounts:social_start",
                    kwargs={"provider": "google", "flow": "register"},
                ),
                {},
            )

        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)
        get_client.assert_not_called()

    def test_google_start_uses_canonical_callback_url(self):
        class FakeGoogleClient:
            callback_uri = None

            def authorize_redirect(self, request, redirect_uri, **kwargs):
                self.callback_uri = redirect_uri
                return HttpResponseRedirect("https://accounts.google.com/")

        fake_client = FakeGoogleClient()
        with patch(
            "accounts.social_views.get_oauth_client",
            return_value=fake_client,
        ):
            response = self.client.post(
                reverse(
                    "accounts:social_start",
                    kwargs={"provider": "google", "flow": "login"},
                ),
                {"next": "/dashboard/"},
                secure=True,
                HTTP_HOST="www.mydigigi.ir",
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://accounts.google.com/")
        self.assertEqual(
            fake_client.callback_uri,
            "https://mydigigi.ir/accounts/social/google/callback/",
        )
        self.assertTrue(
            any(key.startswith("customer-social-state:") for key in self.client.session)
        )
