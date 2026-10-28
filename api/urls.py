from django.urls import include, path
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .admin_pages import admin_page_required

from .views import (
    ApiStatusView,
    BlogPostRatingView,
    BlogPostViewSet,
    MyPaymentOrderListView,
    MyLicenseListView,
    MySubscriptionListView,
    PlanViewSet,
    ProductViewSet,
    ReleaseViewSet,
    TagViewSet,
    CustomerProfileView,
    TokenCreateView,
    TokenRevokeView,
)

app_name = "api"

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("releases", ReleaseViewSet, basename="release")
router.register("plans", PlanViewSet, basename="plan")
router.register("blog/posts", BlogPostViewSet, basename="blog-post")
router.register("blog/tags", TagViewSet, basename="blog-tag")

urlpatterns = [
    path("", admin_page_required(ApiStatusView.as_view()), name="root"),
    path("auth/token/", TokenCreateView.as_view(), name="token-create"),
    path("auth/token/revoke/", TokenRevokeView.as_view(), name="token-revoke"),
    path("account/me/", CustomerProfileView.as_view(), name="account-me"),
    path("account/subscriptions/", MySubscriptionListView.as_view(), name="account-subscriptions"),
    path("account/orders/", MyPaymentOrderListView.as_view(), name="account-orders"),
    path("account/licenses/", MyLicenseListView.as_view(), name="account-licenses"),
    path("blog/posts/<str:slug>/rating/", BlogPostRatingView.as_view(), name="blog-rating"),
    path("schema/", admin_page_required(SpectacularAPIView.as_view()), name="schema"),
    path("docs/", admin_page_required(SpectacularSwaggerView.as_view(url_name="api:schema")), name="docs"),
    path("", include(router.urls)),
]
