from datetime import timedelta
from accounts.models import Customer
from django.test import TestCase, override_settings
from django.urls import reverse
from catalog.models import Plan, Product
from billing.models import PaymentOrder
from subscriptions.models import Subscription

@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    TURNSTILE_ENABLED=False,
)
class PortalPageTests(TestCase):
    def setUp(self):
        self.user = Customer.objects.create_user(username="portal_user", email="portal@example.com", password="a-secure-test-password")
        self.product = Product.objects.create(name="Nebula Vault", slug="nebula-vault", description="A secure workspace.")
        self.plan = Plan.objects.create(product=self.product, name="Monthly", slug="monthly", duration_unit=Plan.DurationUnit.MONTHS, duration_value=1, price_minor_units=1999, currency="USD", device_limit=2)

    def test_public_pages_render(self):
        for url in ("portal:home", "portal:products", "portal:pricing"):
            self.assertEqual(self.client.get(reverse(url)).status_code, 200)
        self.assertEqual(self.client.get(reverse("portal:product_detail", args=[self.product.slug])).status_code, 200)

    def test_homepage_renders_for_authenticated_customer(self):
        self.client.force_login(
            self.user,
            backend="accounts.backends.CustomerAuthenticationBackend",
        )
        response = self.client.get(reverse("portal:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NEBULA VAULT")

    def test_rich_product_description_is_sanitized_and_rendered(self):
        self.product.description = '<p>Visible <strong>formatted</strong> text.</p><script>alert("xss")</script><img src="https://example.com/image.png" onerror="alert(1)">'
        self.product.save()
        response = self.client.get(reverse("portal:product_detail", args=[self.product.slug]))
        self.assertContains(response, "<p>Visible <strong>formatted</strong> text.</p>", html=False)
        self.assertNotContains(response, '<script>alert("xss")</script>', html=False)
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

    def test_registration_creates_inactive_account_pending_email_verification(self):
        response = self.client.post(reverse("accounts:register"), {"username":"new_portal_user","email":"new@example.com","password1":"Sufficiently-long-pass-947!","password2":"Sufficiently-long-pass-947!", "human_check":"on"})
        self.assertEqual(response.status_code, 200)
        customer = Customer.objects.get(email="new@example.com")
        self.assertEqual(customer.username, "new")
        self.assertFalse(customer.is_active)
        self.assertNotIn("_auth_user_id", self.client.session)

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
        self.assertContains(cart_response, "خلاصه سفارش")


    def test_order_remains_pending_without_payment_provider(self):
        self.client.force_login(self.user, backend='accounts.backends.CustomerAuthenticationBackend')
        self.client.post(reverse("portal:create_order", args=[self.plan.pk]))
        order = PaymentOrder.objects.get(user=self.user)
        self.assertEqual(order.status, PaymentOrder.Status.PENDING)
        self.assertIsNone(order.paid_at)


@override_settings(GA4_MEASUREMENT_ID="G-TEST123456")
class AnalyticsConsentTests(TestCase):
    def test_ga4_tag_is_present_but_consent_is_not_assumed(self):
        response = self.client.get(reverse("portal:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-ga4-id="G-TEST123456"')
        self.assertContains(response, 'id="nv-analytics-consent"')
        self.assertContains(response, "data-ga4-accept")
        self.assertContains(response, "data-ga4-reject")
        self.assertContains(response, "portal/js/ga4.js")

    @override_settings(GA4_MEASUREMENT_ID="")
    def test_ga4_is_disabled_without_a_measurement_id(self):
        response = self.client.get(reverse("portal:home"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "portal/js/ga4.js")
        self.assertNotContains(response, 'id="nv-analytics-consent"')

    def test_server_confirmed_auth_event_is_exposed_only_once(self):
        session = self.client.session
        session["ga4_pending_event"] = "login"
        session.save()

        first_response = self.client.get(reverse("portal:home"))
        second_response = self.client.get(reverse("portal:home"))

        self.assertContains(first_response, 'data-ga4-pending-event="login"')
        self.assertContains(second_response, 'data-ga4-pending-event=""')
