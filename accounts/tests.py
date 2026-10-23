from accounts.models import Customer
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AccountBackendTests(TestCase):
    def setUp(self):
        self.user = Customer.objects.create_user(
            username="account_user",
            email="account@example.com",
            password="Secure-test-password-2026!",
        )

    def test_profile_requires_authentication(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_profile_updates_normalized_email_and_names(self):
        self.client.force_login(self.user, backend='accounts.backends.CustomerAuthenticationBackend')
        response = self.client.post(
            reverse("accounts:profile"),
            {"first_name": "Test", "last_name": "User", "email": "  ACCOUNT@example.com  "},
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Test")
        self.assertEqual(self.user.email, "account@example.com")

    def test_profile_rejects_email_used_by_another_user(self):
        Customer.objects.create_user(
            username="another_user", email="other@example.com", password="Secure-test-password-2026!"
        )
        self.client.force_login(self.user, backend='accounts.backends.CustomerAuthenticationBackend')
        response = self.client.post(
            reverse("accounts:profile"),
            {"first_name": "", "last_name": "", "email": "other@example.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account with this email already exists.")

    def test_password_change_keeps_user_signed_in(self):
        self.client.force_login(self.user, backend='accounts.backends.CustomerAuthenticationBackend')
        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": "Secure-test-password-2026!",
                "new_password1": "Another-secure-password-2026!",
                "new_password2": "Another-secure-password-2026!",
            },
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Another-secure-password-2026!"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_password_reset_does_not_disclose_unknown_email(self):
        response = self.client.post(
            reverse("accounts:password_reset"), {"email": "unknown@example.com"}
        )
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_sends_email_for_existing_account(self):
        response = self.client.post(
            reverse("accounts:password_reset"), {"email": self.user.email}
        )
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("accounts/password/reset/", mail.outbox[0].body)
    def test_customer_login_persists_uuid_session_across_requests(self):
        login_response = self.client.post(
            reverse("login"),
            {
                "username": self.user.email,
                "password": "Secure-test-password-2026!",
                "human_check": "on",
            },
        )
        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(login_response.url, reverse("portal:dashboard"))
        self.assertEqual(str(self.client.session["_auth_user_id"]), str(self.user.pk))

        # A second request must restore the UUID-backed Customer from the session.
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)

