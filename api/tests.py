from datetime import timedelta
import hashlib
import secrets

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Customer
from api.models import CustomerAPIToken
from blog.models import BlogPost
from catalog.models import Plan, Product
from licensing.models import License
from subscriptions.models import Subscription


class PublicApiTests(APITestCase):
    def test_api_root_and_product_listing(self):
        product = Product.objects.create(
            name="Nebula Test",
            slug="nebula-test",
            description="Public product",
            is_active=True,
        )
        Product.objects.create(name="Hidden Product", slug="hidden", is_active=False)

        # API discovery is staff-only; product data remains publicly readable.
        root = self.client.get("/api/v1/")
        self.assertEqual(root.status_code, status.HTTP_403_FORBIDDEN)

        staff = get_user_model().objects.create_superuser(
            username="api-admin",
            email="api-admin@example.com",
            password="Strong-admin-password-123!",
        )
        self.client.force_login(staff, backend="django.contrib.auth.backends.ModelBackend")
        root = self.client.get("/api/v1/")
        self.assertEqual(root.status_code, status.HTTP_200_OK)
        self.assertEqual(root.data["version"], "v1")
        self.client.logout()

        response = self.client.get("/api/v1/products/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(product.pk))

    def test_openapi_schema_is_available_to_active_staff_only(self):
        anonymous_response = self.client.get("/api/v1/schema/")
        self.assertEqual(anonymous_response.status_code, status.HTTP_403_FORBIDDEN)

        staff = get_user_model().objects.create_superuser(
            username="schema-admin",
            email="schema-admin@example.com",
            password="Strong-admin-password-123!",
        )
        self.client.force_login(staff, backend="django.contrib.auth.backends.ModelBackend")
        response = self.client.get("/api/v1/schema/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("openapi", response.data)

    def test_only_published_blog_posts_are_public(self):
        BlogPost.objects.create(
            title="Public article",
            slug="public-article",
            content="Public content",
            status=BlogPost.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        BlogPost.objects.create(
            title="Draft article",
            slug="draft-article",
            content="Draft content",
            status=BlogPost.Status.DRAFT,
        )

        response = self.client.get("/api/v1/blog/posts/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["slug"], "public-article")


class CustomerApiAuthenticationTests(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create_user(
            email="customer@example.com",
            password="Strong-password-123!",
            username="customer",
            first_name="Test",
        )

    def create_token(self):
        response = self.client.post(
            "/api/v1/auth/token/",
            {"email": "customer@example.com", "password": "Strong-password-123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["token_type"], "Bearer")
        self.assertIn("access_token", response.data)
        return response.data["access_token"]

    def test_token_is_hashed_and_can_access_customer_profile(self):
        raw_token = self.create_token()
        token = CustomerAPIToken.objects.get(customer=self.customer)
        self.assertNotEqual(token.token_digest, raw_token)
        self.assertEqual(len(token.token_digest), 64)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw_token}")
        response = self.client.get("/api/v1/account/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.customer.email)

    def test_customer_can_update_profile_but_not_email_or_privileges(self):
        raw_token = self.create_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw_token}")
        response = self.client.patch(
            "/api/v1/account/me/",
            {
                "first_name": "Updated",
                "email": "attacker@example.com",
                "is_banned": True,
                "is_active": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.first_name, "Updated")
        self.assertEqual(self.customer.email, "customer@example.com")
        self.assertFalse(self.customer.is_banned)
        self.assertTrue(self.customer.is_active)

    def test_revoked_token_is_rejected(self):
        raw_token = self.create_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw_token}")
        revoke = self.client.post("/api/v1/auth/token/revoke/", {}, format="json")
        self.assertEqual(revoke.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get("/api/v1/account/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_inactive_or_banned_customers_cannot_get_tokens(self):
        self.customer.is_banned = True
        self.customer.save(update_fields=("is_banned",))
        response = self.client.post(
            "/api/v1/auth/token/",
            {"email": self.customer.email, "password": "Strong-password-123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_license_endpoint_returns_only_safe_license_metadata(self):
        raw_token = secrets.token_urlsafe(48)
        CustomerAPIToken.objects.create(
            customer=self.customer,
            token_prefix=raw_token[:12],
            token_digest=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
            expires_at=timezone.now() + timedelta(days=30),
        )
        product = Product.objects.create(name="Licensed Product", is_active=True)
        plan = Plan.objects.create(
            product=product,
            name="Monthly",
            slug="monthly",
            duration_unit="months",
            duration_value=1,
            price_minor_units=1000,
            currency="IRR",
        )
        now = timezone.now()
        subscription = Subscription.objects.create(
            user=self.customer,
            product=product,
            kind=Subscription.Kind.PAID,
            status=Subscription.Status.ACTIVE,
            plan=plan,
            starts_at=now,
            expires_at=now + timedelta(days=30),
        )
        License.objects.create(
            subscription=subscription,
            key_digest=hashlib.sha256(b"private-license-key").hexdigest(),
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw_token}")
        response = self.client.get("/api/v1/account/licenses/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        license_data = response.data["results"][0]
        self.assertEqual(license_data["product"], product.slug)
        self.assertNotIn("key_digest", license_data)
        self.assertNotIn("display_key", license_data)

    def test_token_has_expiry(self):
        self.create_token()
        token = CustomerAPIToken.objects.get(customer=self.customer)
        self.assertGreater(token.expires_at, timezone.now() + timedelta(days=29))
