from datetime import timedelta
from accounts.models import Customer
from django.test import TestCase
from django.urls import reverse
from catalog.models import Plan, Product
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
        self.client.force_login(self.user)
        response = self.client.post(reverse("portal:start_trial", args=[self.product.slug]))
        self.assertEqual(response.status_code, 302)
        sub = Subscription.objects.get(user=self.user, product=self.product)
        self.assertEqual(sub.kind, Subscription.Kind.TRIAL)
        self.assertLessEqual(sub.expires_at - sub.starts_at, timedelta(days=7))

    def test_order_remains_pending_without_payment_provider(self):
        from billing.models import PaymentOrder
        self.client.force_login(self.user)
        self.client.post(reverse("portal:create_order", args=[self.plan.pk]))
        order = PaymentOrder.objects.get(user=self.user)
        self.assertEqual(order.status, PaymentOrder.Status.PENDING)
        self.assertIsNone(order.paid_at)
