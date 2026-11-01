from accounts.models import Customer
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", TURNSTILE_ENABLED=False)
class AccountBackendTests(TestCase):
    def setUp(self):
        # The production database cache is shared by request throttles; clear it
        # between tests so one test's rate limit cannot leak into another.
        cache.clear()
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

    def test_changing_email_requires_reverification(self):
        self.client.force_login(self.user, backend="accounts.backends.CustomerAuthenticationBackend")
        response = self.client.post(
            reverse("accounts:profile"),
            {"username": self.user.username, "first_name": "", "last_name": "", "email": "new-address@example.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new-address@example.com")
        self.assertFalse(self.user.is_active)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("accounts/verify/", mail.outbox[0].body)

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
        self.assertContains(response, "حسابی با این نشانی ایمیل از قبل وجود دارد.")

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
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["purpose"], "password_reset")
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_sends_email_for_existing_account(self):
        response = self.client.post(
            reverse("accounts:password_reset"), {"email": self.user.email}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["purpose"], "password_reset")
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

    def test_unverified_customer_cannot_sign_in(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.client.post(
            reverse("login"),
            {"username": self.user.email, "password": "Secure-test-password-2026!", "human_check": "on"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_verification_link_activates_account_and_is_single_use(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        from accounts.views import email_verification_token
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = email_verification_token.make_token(self.user)
        response = self.client.get(reverse("accounts:verify_email", args=[uid, token]))
        self.assertRedirects(response, reverse("portal:dashboard"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        response = self.client.get(reverse("accounts:verify_email", args=[uid, token]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["already_verified"])

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


    def test_verification_code_activates_account(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.client.post(
            reverse("accounts:resend_verification"), {"email": self.user.email}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        import re
        code_match = re.search(r"(?m)^([0-9]{6})$", mail.outbox[0].body)
        self.assertIsNotNone(code_match)
        response = self.client.post(
            reverse("accounts:verify_email_code"),
            {"email": self.user.email, "code": code_match.group(1)},
        )
        self.assertRedirects(response, reverse("portal:dashboard"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_password_reset_email_contains_link_and_six_digit_code(self):
        response = self.client.post(
            reverse("accounts:password_reset"), {"email": self.user.email}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["purpose"], "password_reset")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("accounts/password/reset/", mail.outbox[0].body)
        import re
        self.assertRegex(mail.outbox[0].body, r"(?m)^([0-9]{6})$")

    def test_password_reset_code_generates_customer_reset_link(self):
        from accounts.models import AccountEmailLog
        from accounts.views import _code_digest
        from django.utils import timezone
        from datetime import timedelta
        entry = AccountEmailLog.objects.create(
            customer=self.user, recipient=self.user.email,
            purpose=AccountEmailLog.Purpose.PASSWORD_RESET,
            status=AccountEmailLog.Status.SENT,
            sent_at=timezone.now(), expires_at=timezone.now() + timedelta(minutes=15),
            code_hash=_code_digest("482916"),
        )
        response = self.client.post(
            reverse("accounts:password_reset_code"),
            {"email": self.user.email, "code": "482916"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/password/reset/", response.url)
        entry.refresh_from_db()
        self.assertEqual(entry.status, AccountEmailLog.Status.USED)

    def test_email_history_is_registered_in_admin(self):
        from django.contrib import admin
        from accounts.models import AccountEmailLog
        self.assertIn(AccountEmailLog, admin.site._registry)


    def test_customer_login_locks_after_five_failed_attempts(self):
        payload = {
            "username": self.user.email,
            "password": "Definitely-wrong-password!",
            "human_check": "on",
        }
        for attempt in range(1, 6):
            response = self.client.post(reverse("login"), payload)
            if attempt < 5:
                self.assertEqual(response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 429)
                self.assertContains(response, "موقتاً محدود شده است", status_code=429)
        # Further submissions remain blocked during the 15-minute window.
        response = self.client.post(reverse("login"), payload)
        self.assertEqual(response.status_code, 429)

    def test_successful_customer_login_clears_failed_attempt_counter(self):
        from django.core.cache import cache
        from unittest.mock import patch

        cache_key = "customer-login-failures:test-success-clears"
        cache.set(cache_key, 2, timeout=900)
        with patch("accounts.views.CustomerLoginView._login_attempt_key", return_value=cache_key):
            response = self.client.post(
                reverse("login"),
                {
                    "username": self.user.email,
                    "password": "Secure-test-password-2026!",
                    "human_check": "on",
                },
            )
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(cache.get(cache_key))


    def test_customer_login_remember_me_is_checked_by_default(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"]["remember_me"].value())

    def test_customer_two_factor_is_disabled_by_default_and_can_be_enabled(self):
        import pyotp

        self.assertFalse(self.user.two_factor_enabled)
        import hashlib
        import secrets
        from datetime import timedelta
        from django.utils import timezone
        from api.models import CustomerAPIToken
        raw_api_token = secrets.token_urlsafe(48)
        api_token = CustomerAPIToken.objects.create(
            customer=self.user,
            token_prefix=raw_api_token[:12],
            token_digest=hashlib.sha256(raw_api_token.encode("utf-8")).hexdigest(),
            expires_at=timezone.now() + timedelta(days=30),
        )
        self.client.force_login(self.user, backend="accounts.backends.CustomerAuthenticationBackend")
        response = self.client.get(reverse("accounts:two_factor_settings"))
        secret = response.context["two_factor_secret"]
        response = self.client.post(
            reverse("accounts:two_factor_settings"),
            {"security_action": "enable_two_factor", "current_password": "Secure-test-password-2026!", "otp_token": pyotp.TOTP(secret).now()},
        )
        self.assertRedirects(response, reverse("accounts:two_factor_settings"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.two_factor_enabled)
        api_token.refresh_from_db()
        self.assertIsNotNone(api_token.revoked_at)
        from accounts.two_factor import decrypt_totp_secret
        self.assertEqual(decrypt_totp_secret(self.user.two_factor_secret), secret)

    def test_customer_two_factor_is_required_during_login(self):
        import pyotp

        secret = pyotp.random_base32()
        self.user.two_factor_secret = __import__("accounts.two_factor", fromlist=["encrypt_totp_secret"]).encrypt_totp_secret(secret)
        self.user.two_factor_enabled = True
        self.user.save(update_fields=["two_factor_secret", "two_factor_enabled"])
        response = self.client.post(
            reverse("login"),
            {"username": self.user.email, "password": "Secure-test-password-2026!", "otp_token": "000000", "human_check": "on"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, "کد تأیید دومرحله‌ای نامعتبر است")

    def test_customer_two_factor_valid_code_allows_login_and_remember_me(self):
        import pyotp

        secret = pyotp.random_base32()
        self.user.two_factor_secret = __import__("accounts.two_factor", fromlist=["encrypt_totp_secret"]).encrypt_totp_secret(secret)
        self.user.two_factor_enabled = True
        self.user.save(update_fields=["two_factor_secret", "two_factor_enabled"])
        response = self.client.post(
            reverse("login"),
            {"username": self.user.email, "password": "Secure-test-password-2026!", "otp_token": pyotp.TOTP(secret).now(), "remember_me": "on", "human_check": "on"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(str(self.client.session["_auth_user_id"]), str(self.user.pk))
        self.assertGreater(self.client.session.get_expiry_age(), 60 * 60 * 24 * 13)

    def test_customer_profile_accepts_valid_avatar_upload(self):
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile

        image_buffer = BytesIO()
        Image.new("RGB", (32, 32), "blue").save(image_buffer, format="PNG")
        upload = SimpleUploadedFile("profile.png", image_buffer.getvalue(), content_type="image/png")
        self.client.force_login(self.user, backend="accounts.backends.CustomerAuthenticationBackend")
        response = self.client.post(
            reverse("accounts:profile"),
            {"username": self.user.username, "first_name": "", "last_name": "", "email": self.user.email, "avatar": upload},
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.avatar.name.startswith("avatars/"))

    def test_staff_two_factor_is_required_for_admin_login(self):
        import pyotp
        from django.contrib.auth import get_user_model

        staff = get_user_model().objects.create_superuser(
            username="totp_admin", email="totp-admin@example.com",
            password="Secure-admin-password-2026!",
        )
        secret = pyotp.random_base32()
        staff.two_factor_secret = __import__("accounts.two_factor", fromlist=["encrypt_totp_secret"]).encrypt_totp_secret(secret)
        staff.two_factor_enabled = True
        staff.save(update_fields=["two_factor_secret", "two_factor_enabled"])
        response = self.client.post(
            "/admin/login/",
            {"username": staff.username, "password": "Secure-admin-password-2026!", "otp_token": pyotp.TOTP(secret).now(), "remember_me": "on", "next": "/admin/"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(str(self.client.session["_auth_user_id"]), str(staff.pk))

    def test_staff_account_page_is_available_to_staff_and_avatar_form_is_present(self):
        from django.contrib.auth import get_user_model

        staff = get_user_model().objects.create_superuser(
            username="profile_admin", email="profile-admin@example.com",
            password="Secure-admin-password-2026!",
        )
        self.assertFalse(staff.two_factor_enabled)
        self.client.force_login(staff, backend="django.contrib.auth.backends.ModelBackend")
        response = self.client.get("/admin/account/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Profile photo and details")
        self.assertContains(response, "Two-factor authentication")

    def test_admin_login_remember_me_is_checked_by_default(self):
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"]["remember_me"].value())


    def test_staff_can_enable_two_factor_with_password_and_authenticator_code(self):
        import pyotp
        from django.contrib.auth import get_user_model
        from accounts.two_factor import decrypt_totp_secret

        staff = get_user_model().objects.create_superuser(
            username="enroll_admin", email="enroll-admin@example.com",
            password="Secure-admin-password-2026!",
        )
        self.client.force_login(staff, backend="django.contrib.auth.backends.ModelBackend")
        response = self.client.get("/admin/account/")
        self.assertEqual(response.status_code, 200)
        secret = response.context["two_factor_secret"]
        response = self.client.post(
            "/admin/account/",
            {
                "security_action": "enable_two_factor",
                "current_password": "Secure-admin-password-2026!",
                "otp_token": pyotp.TOTP(secret).now(),
            },
        )
        self.assertRedirects(response, "/admin/account/")
        staff.refresh_from_db()
        self.assertTrue(staff.two_factor_enabled)
        self.assertEqual(decrypt_totp_secret(staff.two_factor_secret), secret)

    def test_staff_can_upload_a_profile_photo(self):
        from io import BytesIO
        from PIL import Image
        from django.contrib.auth import get_user_model
        from django.core.files.uploadedfile import SimpleUploadedFile

        staff = get_user_model().objects.create_superuser(
            username="avatar_admin", email="avatar-admin@example.com",
            password="Secure-admin-password-2026!",
        )
        image_buffer = BytesIO()
        Image.new("RGB", (32, 32), "green").save(image_buffer, format="PNG")
        upload = SimpleUploadedFile("staff.png", image_buffer.getvalue(), content_type="image/png")
        self.client.force_login(staff, backend="django.contrib.auth.backends.ModelBackend")
        response = self.client.post(
            "/admin/account/",
            {
                "account_action": "profile",
                "first_name": "Admin",
                "last_name": "Photo",
                "email": staff.email,
                "avatar": upload,
            },
        )
        self.assertRedirects(response, "/admin/account/")
        staff.refresh_from_db()
        self.assertTrue(staff.avatar.name.startswith("avatars/"))
