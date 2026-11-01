from rest_framework import serializers

from accounts.models import Customer
from billing.models import PaymentOrder
from blog.models import BlogPost, BlogPostRating, Tag
from catalog.models import Plan, Product, Release
from licensing.models import License, LicenseActivation
from subscriptions.models import Subscription


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "name", "slug", "description", "website_url", "created_at", "updated_at")
        read_only_fields = fields


class ReleaseSerializer(serializers.ModelSerializer):
    product = serializers.SlugRelatedField(read_only=True, slug_field="slug")

    class Meta:
        model = Release
        fields = (
            "id", "product", "version", "platform", "architecture",
            "download_url", "sha256", "release_notes", "published_at",
        )
        read_only_fields = fields


class PlanSerializer(serializers.ModelSerializer):
    product = serializers.SlugRelatedField(read_only=True, slug_field="slug")

    class Meta:
        model = Plan
        fields = (
            "id", "product", "name", "slug", "duration_unit", "duration_value",
            "price_minor_units", "currency", "device_limit",
        )
        read_only_fields = fields


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name")
        read_only_fields = fields


class BlogPostSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    reading_minutes = serializers.IntegerField(read_only=True)
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = (
            "uuid", "title", "slug", "excerpt", "content", "cover_url", "category",
            "tags", "is_featured", "published_at", "updated_at", "reading_minutes",
        )
        read_only_fields = fields

    def get_cover_url(self, obj):
        if not obj.img:
            return None
        try:
            request = self.context.get("request")
            url = obj.img.url
            return request.build_absolute_uri(url) if request else url
        except (ValueError, OSError):
            return None


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("id", "email", "username", "first_name", "last_name", "date_joined")
        read_only_fields = ("id", "email", "date_joined")


class SubscriptionSerializer(serializers.ModelSerializer):
    product = serializers.SlugRelatedField(read_only=True, slug_field="slug")
    plan = serializers.SlugRelatedField(read_only=True, slug_field="slug")

    class Meta:
        model = Subscription
        fields = (
            "id", "product", "kind", "status", "plan", "starts_at", "expires_at",
            "created_at", "updated_at",
        )
        read_only_fields = fields


class PaymentOrderItemSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    product_name = serializers.CharField(read_only=True)
    plan_name = serializers.CharField(read_only=True)
    amount_minor_units = serializers.IntegerField(read_only=True)
    currency = serializers.CharField(read_only=True)
    duration_value = serializers.IntegerField(read_only=True)
    duration_unit = serializers.CharField(read_only=True)
    device_limit = serializers.IntegerField(read_only=True)


class PaymentOrderSerializer(serializers.ModelSerializer):
    items = PaymentOrderItemSerializer(many=True, read_only=True)
    plan = serializers.SlugRelatedField(read_only=True, slug_field="slug")

    class Meta:
        model = PaymentOrder
        fields = (
            "id", "order_number", "plan", "items", "amount_minor_units",
            "currency", "status", "paid_at", "created_at", "updated_at",
        )
        read_only_fields = fields


class BlogRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogPostRating
        fields = ("score", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")

    def validate_score(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Score must be between 1 and 5.")
        return value


class TokenLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    otp_token = serializers.CharField(required=False, write_only=True, max_length=12)
    email_otp_token = serializers.CharField(required=False, write_only=True, max_length=6)
    recovery_code = serializers.CharField(required=False, write_only=True, max_length=16)


class TokenResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    token_type = serializers.ChoiceField(choices=("Bearer",))
    expires_at = serializers.DateTimeField()
    customer = CustomerProfileSerializer()


class LicenseActivationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LicenseActivation
        fields = (
            "id", "device_label", "app_version", "is_active",
            "first_activated_at", "last_seen_at", "deactivated_at",
        )
        read_only_fields = fields


class CustomerLicenseSerializer(serializers.ModelSerializer):
    product = serializers.SlugRelatedField(
        source="subscription.product", read_only=True, slug_field="slug"
    )
    starts_at = serializers.DateTimeField(source="subscription.starts_at", read_only=True)
    expires_at = serializers.DateTimeField(source="subscription.expires_at", read_only=True)
    subscription_status = serializers.CharField(source="subscription.status", read_only=True)
    device_limit = serializers.IntegerField(read_only=True, source="activation_limit")
    active_devices = serializers.IntegerField(read_only=True, source="active_activation_count")
    is_entitled = serializers.BooleanField(read_only=True)
    activations = LicenseActivationSerializer(many=True, read_only=True)

    class Meta:
        model = License
        fields = (
            "id", "product", "status", "subscription_status", "is_entitled",
            "starts_at", "expires_at", "device_limit", "active_devices",
            "activations", "created_at", "updated_at", "last_validated_at",
        )
        read_only_fields = fields
