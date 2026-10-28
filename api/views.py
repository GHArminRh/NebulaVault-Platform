import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth import authenticate
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle
from rest_framework.views import APIView

from accounts.models import Customer
from billing.models import PaymentOrder
from blog.models import BlogPost, BlogPostRating, Tag
from catalog.models import Plan, Product, Release
from subscriptions.models import Subscription

from .authentication import CustomerBearerAuthentication, CustomerSessionAuthentication
from .models import CustomerAPIToken
from .permissions import IsCustomer
from .serializers import (
    BlogPostSerializer,
    BlogRatingSerializer,
    CustomerProfileSerializer,
    PaymentOrderSerializer,
    PlanSerializer,
    ProductSerializer,
    ReleaseSerializer,
    SubscriptionSerializer,
    TagSerializer,
)


class TokenLoginThrottle(AnonRateThrottle):
    scope = "token_login"


class TokenCreateView(APIView):
    """Issue a one-time-visible 30-day customer Bearer token."""

    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()
    throttle_classes = (TokenLoginThrottle,)

    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        password = request.data.get("password", "")
        if not email or not isinstance(password, str) or not password:
            return Response(
                {"detail": "Email and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer = Customer.objects.filter(email__iexact=email).first()
        if customer is None or not customer.check_password(password):
            raise AuthenticationFailed("Invalid email or password.")
        if not customer.is_active or customer.is_banned:
            raise AuthenticationFailed("This account cannot access the API.")

        raw_token = secrets.token_urlsafe(48)
        token = CustomerAPIToken.objects.create(
            customer=customer,
            token_prefix=raw_token[:12],
            token_digest=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
            expires_at=timezone.now() + timedelta(days=30),
        )
        return Response(
            {
                "access_token": raw_token,
                "token_type": "Bearer",
                "expires_at": token.expires_at,
                "customer": CustomerProfileSerializer(customer).data,
            },
            status=status.HTTP_201_CREATED,
        )


class TokenRevokeView(APIView):
    authentication_classes = (CustomerBearerAuthentication, CustomerSessionAuthentication)
    permission_classes = (IsCustomer,)

    def post(self, request):
        token = request.auth
        if not isinstance(token, CustomerAPIToken):
            return Response(
                {"detail": "Use a Bearer token to revoke that API token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if token.revoked_at is None:
            token.revoked_at = timezone.now()
            token.save(update_fields=("revoked_at",))
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    lookup_field = "slug"
    lookup_value_regex = r"[-a-zA-Z0-9_]+"
    queryset = Product.objects.filter(is_active=True).order_by("name")
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "created_at", "updated_at")
    ordering = ("name",)


class ReleaseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReleaseSerializer
    lookup_field = "id"
    queryset = Release.objects.filter(
        is_published=True,
        product__is_active=True,
    ).select_related("product")
    filterset_fields = ("product__slug", "platform", "architecture")
    search_fields = ("version", "release_notes", "product__name")
    ordering_fields = ("published_at", "version", "created_at")
    ordering = ("-published_at",)


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PlanSerializer
    lookup_field = "id"
    queryset = Plan.objects.filter(
        is_active=True,
        product__is_active=True,
    ).select_related("product")
    filterset_fields = ("product__slug", "duration_unit", "currency")
    search_fields = ("name", "slug", "product__name")
    ordering_fields = ("sort_order", "price_minor_units", "name")
    ordering = ("sort_order", "price_minor_units", "name")


class BlogPostViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BlogPostSerializer
    lookup_field = "slug"
    lookup_value_regex = r"[-a-zA-Z0-9_]+"
    queryset = BlogPost.objects.filter(
        status=BlogPost.Status.PUBLISHED,
        published_at__isnull=False,
    ).prefetch_related("tags")
    filterset_fields = ("category", "is_featured", "tags__id")
    search_fields = ("title", "excerpt", "content", "category", "tags__name")
    ordering_fields = ("published_at", "created_at", "updated_at", "title")
    ordering = ("-is_featured", "-published_at")


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TagSerializer
    queryset = Tag.objects.all()
    lookup_field = "id"
    search_fields = ("name",)
    ordering_fields = ("name",)
    ordering = ("name",)


class CustomerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = CustomerProfileSerializer
    authentication_classes = (CustomerBearerAuthentication, CustomerSessionAuthentication)
    permission_classes = (IsCustomer,)

    def get_object(self):
        return self.request.user


class MySubscriptionListView(generics.ListAPIView):
    serializer_class = SubscriptionSerializer
    authentication_classes = (CustomerBearerAuthentication, CustomerSessionAuthentication)
    permission_classes = (IsCustomer,)
    ordering_fields = ("created_at", "starts_at", "expires_at", "status")
    ordering = ("-created_at",)

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user).select_related("product", "plan")


class MyPaymentOrderListView(generics.ListAPIView):
    serializer_class = PaymentOrderSerializer
    authentication_classes = (CustomerBearerAuthentication, CustomerSessionAuthentication)
    permission_classes = (IsCustomer,)
    ordering_fields = ("created_at", "paid_at", "status", "amount_minor_units")
    ordering = ("-created_at",)

    def get_queryset(self):
        return (
            PaymentOrder.objects.filter(user=self.request.user)
            .select_related("plan")
            .prefetch_related("items")
        )


class BlogPostRatingView(APIView):
    authentication_classes = (CustomerBearerAuthentication, CustomerSessionAuthentication)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "ratings"

    def get_permissions(self):
        return [permissions.AllowAny()] if self.request.method == "GET" else [IsCustomer()]

    def get_post(self):
        return get_object_or_404(
            BlogPost,
            slug=self.kwargs["slug"],
            status=BlogPost.Status.PUBLISHED,
            published_at__isnull=False,
        )

    def get(self, request, slug):
        post = self.get_post()
        stats = BlogPostRating.objects.filter(post=post).aggregate(
            average=Avg("score"),
            count=Count("id"),
        )
        own_score = None
        if getattr(request.user, "is_authenticated", False) and hasattr(request.user, "email"):
            own_score = BlogPostRating.objects.filter(post=post, user=request.user).values_list(
                "score", flat=True
            ).first()
        return Response(
            {
                "post": post.slug,
                "average": round(stats["average"], 2) if stats["average"] is not None else None,
                "count": stats["count"],
                "my_score": own_score,
            }
        )

    def post(self, request, slug):
        post = self.get_post()
        serializer = BlogRatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rating, created = BlogPostRating.objects.update_or_create(
            post=post,
            user=request.user,
            defaults={"score": serializer.validated_data["score"]},
        )
        return Response(
            BlogRatingSerializer(rating).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ApiStatusView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    def get(self, request):
        return Response(
            {
                "name": "Nebula Vault API",
                "version": "v1",
                "status": "ok",
                "authentication": ["Bearer token", "customer session"],
                "documentation": "/api/docs/",
                "schema": "/api/schema/",
            }
        )
