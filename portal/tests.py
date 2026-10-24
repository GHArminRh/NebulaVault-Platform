from datetime import timedelta
from accounts.models import Customer
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from catalog.models import Plan, Product
from billing.models import PaymentAttempt, PaymentOrder
from subscriptions.models import Subscription

class PortalPageTests(TestCase):
    def setUp(self):
        self.user = Customer.objects.create_user(username="portal_user", email="portal@example.com", password="a-secure-test-password")
        self.product = Product.objects.create(name="Nebula Vault", slug="nebula-vault", description="A secure workspace.")
        self.plan = Plan.objects.create(product=self.product, name="Monthly", slug="monthly", duration_unit=Plan.DurationUnit.MONTHS, duration_value=1, price_minor_units=1999, currency="USD", device_limit=2)

    def test_public_pages_render(self):
        for url in ("portal:home", "portal:products", "portal:pricing"):
            self.assertEqual(self.client.get(reverse(url)).status_code, 200)
        self.assertEqual(self.client.get(reverse("portal:product_detail", args=[self.product.slug])).status_code, 200)

    def test_rich_product_description_is_sanitized_and_rendered(self):
        self.product.description = '<p>Visible <strong>formatted</strong> text.</p><script>alert("xss")</script><img src="https://example.com/image.png" onerror="alert(1)">'
        self.product.save()
        response = self.client.get(reverse("portal:product_detail", args=[self.product.slug]))
        self.assertContains(response, "<p>Visible <strong>formatted</strong> text.</p>", html=False)
        self.assertNotContains(response, "<script")
        self.assertNotContains(response, "onerror")
        self.assertNotContains(response, "alert(")

    def test_rich_description_only_allows_sandboxed_video_providers(self):
        self.product.description = (
            '<p>Video</p>'
            '<iframe src="https://www.youtube.com/embed/abcdefghijk" onload="alert(1)"></iframe>'
            '<iframe src="https://evil.example/embed/abcdefghijk"></iframe>'
        )
        self.product.save()
        response = self.client.get(reverse("portal:product_detail", args=[self.product.slug]))
        self.assertContains(response, 'youtube.com/embed/abcdefghijk', html=False)
        self.assertContains(response, 'sandbox=', html=False)
        self.assertNotContains(response, 'evil.example')
        self.assertNotContains(response, 'onload=')
        self.assertNotContains(response, 'alert(')

    def test_editor_image_upload_requires_staff(self):
        response = self.client.post(reverse("editor-image-upload"), {})
        self.assertEqual(response.status_code, 403)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("portal:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_registration_creates_account_and_signs_in(self):
        response = self.client.post(reverse("accounts:register"), {"username":"new_portal_user","email":"new@example.com","password1":"Sufficiently-long-pass-947!","password2":"Sufficiently-long-pass-947!", "human_check":"on"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Customer.objects.filter(username="new_portal_user", email="new@example.com").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_trial_starts_for_signed_in_user(self):
        self.client.force_login(self.user, backend='accounts.backends.CustomerAuthenticationBackend')
        response = self.client.post(reverse("portal:start_trial", args=[self.product.slug]))
        self.assertEqual(response.status_code, 302)
        sub = Subscription.objects.get(user=self.user, product=self.product)
        self.assertEqual(sub.kind, Subscription.Kind.TRIAL)
        self.assertLessEqual(sub.expires_at - sub.starts_at, timedelta(days=7))

    def test_cart_can_be_used_before_sign_in(self):
        response = self.client.post(reverse("portal:cart_add", args=[self.plan.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get("nebula_cart"), [str(self.plan.pk)])
        cart_response = self.client.get(reverse("portal:cart"))
        self.assertEqual(cart_response.status_code, 200)
        self.assertContains(cart_response, self.plan.name)
        self.assertContains(cart_response, "Pay &amp; complete order")

    @override_settings(NEBULA_MOCK_PAYMENTS=True)
    def test_demo_checkout_marks_order_paid_and_activates_subscription(self):
        self.client.force_login(
            self.user,
            backend="accounts.backends.CustomerAuthenticationBackend",
        )
        self.client.post(reverse("portal:cart_add", args=[self.plan.pk]))
        response = self.client.post(reverse("portal:checkout"))
        self.assertRedirects(response, reverse("portal:orders"))

        order = PaymentOrder.objects.get(user=self.user, plan=self.plan)
        self.assertEqual(order.status, PaymentOrder.Status.PAID)
        self.assertIsNotNone(order.paid_at)

        attempt = PaymentAttempt.objects.get(order=order)
        self.assertEqual(attempt.provider, "mock")
        self.assertEqual(attempt.status, PaymentAttempt.Status.SUCCEEDED)

        subscription = Subscription.objects.get(user=self.user, plan=self.plan)
        self.assertEqual(subscription.status, Subscription.Status.ACTIVE)
        self.assertEqual(subscription.kind, Subscription.Kind.PAID)
        self.assertGreater(subscription.expires_at, subscription.starts_at)
        self.assertEqual(self.client.session.get("nebula_cart"), [])

    def test_order_remains_pending_without_payment_provider(self):
        from billing.models import PaymentOrder
        self.client.force_login(self.user, backend='accounts.backends.CustomerAuthenticationBackend')
        self.client.post(reverse("portal:create_order", args=[self.plan.pk]))
        order = PaymentOrder.objects.get(user=self.user)
        self.assertEqual(order.status, PaymentOrder.Status.PENDING)
        self.assertIsNone(order.paid_at)


class StaffSessionIsolationTests(TestCase):
    def test_admin_user_is_not_treated_as_customer_on_public_site(self):
        StaffUser = get_user_model()
        staff = StaffUser.objects.create_user(
            username="site_admin", password="admin-test-password", is_staff=True, is_superuser=True
        )
        self.client.force_login(staff, backend="django.contrib.auth.backends.ModelBackend")

        response = self.client.get(reverse("portal:home"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_staff_session_remains_available_in_django_admin(self):
        StaffUser = get_user_model()
        staff = StaffUser.objects.create_user(
            username="site_admin_2", password="admin-test-password", is_staff=True, is_superuser=True
        )
        self.client.force_login(staff, backend="django.contrib.auth.backends.ModelBackend")

        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
