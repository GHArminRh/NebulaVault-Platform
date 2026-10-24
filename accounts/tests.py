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
    def test_registration_generates_username_from_email_local_part(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "email": "GArminRh@gmail.com",
                "password1": "Secure-registration-password-2026!",
                "password2": "Secure-registration-password-2026!",
                "human_check": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        customer = Customer.objects.get(email__iexact="GArminRh@gmail.com")
        self.assertEqual(customer.username, "GArminRh")
        self.assertFalse(customer.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("accounts/verify/", mail.outbox[0].body)

    def test_registration_adds_suffix_when_generated_username_is_taken(self):
        Customer.objects.create_user(
            username="GArminRh",
            email="existing@example.com",
            password="Secure-existing-password-2026!",
        )
        response = self.client.post(
            reverse("accounts:register"),
            {
                "email": "GArminRh@gmail.com",
                "password1": "Secure-registration-password-2026!",
                "password2": "Secure-registration-password-2026!",
                "human_check": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        customer = Customer.objects.get(email__iexact="GArminRh@gmail.com")
        self.assertEqual(customer.username, "GArminRh2")

    def test_profile_allows_customer_to_change_username(self):
        self.client.force_login(self.user, backend="accounts.backends.CustomerAuthenticationBackend")
        response = self.client.post(
            reverse("accounts:profile"),
            {
                "username": "new_account_name",
                "first_name": "Test",
                "last_name": "User",
                "email": self.user.email,
            },
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "new_account_name")

    def test_verification_link_activates_account_and_is_single_use(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        from accounts.views import email_verification_token
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = email_verification_token.make_token(self.user)
        response = self.client.get(reverse("accounts:verify_email", args=[uid, token]))
        self.assertRedirects(response, reverse("login"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        response = self.client.get(reverse("accounts:verify_email", args=[uid, token]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already verified")

    def test_resend_verification_does_not_disclose_unknown_email(self):
        response = self.client.post(reverse("accounts:resend_verification"), {"email": "unknown@example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_admin_login_clears_existing_customer_uuid_session(self):
        from django.contrib.auth import get_user_model

        staff = get_user_model().objects.create_superuser(
            username="admin_test",
            email="admin@example.com",
            password="Secure-admin-password-2026!",
        )
        self.client.force_login(
            self.user, backend="accounts.backends.CustomerAuthenticationBackend"
        )

        response = self.client.post(
            "/admin/login/",
            {
                "username": staff.username,
                "password": "Secure-admin-password-2026!",
                "next": "/admin/",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith("/admin/"))
        self.assertEqual(str(self.client.session["_auth_user_id"]), str(staff.pk))

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

    def test_staff_user_uses_uuid4_primary_key(self):
        import uuid
        from django.contrib.auth import get_user_model

        StaffUser = get_user_model()
        staff = StaffUser.objects.create_user(
            username="uuid_staff",
            email="uuid_staff@example.com",
            password="Secure-staff-password-2026!",
        )
        self.assertIsInstance(staff.pk, uuid.UUID)
        self.assertEqual(staff.pk.version, 4)

    def test_staff_uuid_session_survives_following_request(self):
        from django.contrib.auth import get_user_model

        staff = get_user_model().objects.create_superuser(
            username="uuid_admin",
            email="uuid_admin@example.com",
            password="Secure-admin-password-2026!",
        )
        self.client.force_login(staff, backend="django.contrib.auth.backends.ModelBackend")
        self.assertEqual(str(self.client.session["_auth_user_id"]), str(staff.pk))

        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(self.client.session["_auth_user_id"]), str(staff.pk))


    def test_permission_group_uses_uuid4_primary_key(self):
        import uuid
        from staff.models import Group

        group = Group.objects.create(name="UUID test group")
        self.assertIsInstance(group.pk, uuid.UUID)
        self.assertEqual(group.pk.version, 4)

    def test_staff_user_can_use_custom_uuid_permission_group(self):
        from staff.models import Group
        from django.contrib.auth import get_user_model

        staff = get_user_model().objects.create_user(
            username="group_member",
            email="group_member@example.com",
            password="Secure-staff-password-2026!",
        )
        group = Group.objects.create(name="staff-test-group")
        staff.groups.add(group)

        self.assertIn(group, staff.groups.all())
        self.assertIn(staff, group.user_set.all())

    def test_builtin_integer_group_is_not_registered_in_admin(self):
        from django.contrib import admin
        from django.contrib.auth.models import Group as DjangoAuthGroup
        from staff.models import Group

        self.assertNotIn(DjangoAuthGroup, admin.site._registry)
        self.assertIn(Group, admin.site._registry)
