from django.urls import path
from . import views
from .cms_home import cms_home

app_name = "portal"
urlpatterns = [
    # Preserve the portal:home URL name used by the shared header/footer, but
    # render the published CMS homepage at / with the original storefront as fallback.
    path("", cms_home, name="home"),
    path("products/", views.products, name="products"),
    path("products/<slug:slug>/", views.product_detail, name="product_detail"),
    path("pricing/", views.pricing, name="pricing"),
    path("cart/", views.cart, name="cart"),
    path("cart/add/<uuid:plan_id>/", views.cart_add, name="cart_add"),
    path("cart/remove/<uuid:plan_id>/", views.cart_remove, name="cart_remove"),
    path("cart/clear/", views.cart_clear, name="cart_clear"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("subscriptions/", views.subscriptions, name="subscriptions"),
    path("orders/", views.orders, name="orders"),
    path("orders/create/<uuid:plan_id>/", views.create_order, name="create_order"),
    path("trial/<slug:slug>/", views.start_trial, name="start_trial"),
]
