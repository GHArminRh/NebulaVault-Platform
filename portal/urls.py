from django.urls import path
from . import views

app_name = "portal"
urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.products, name="products"),
    path("products/<slug:slug>/", views.product_detail, name="product_detail"),
    path("pricing/", views.pricing, name="pricing"),
    path("cart/", views.cart, name="cart"),
    path("cart/add/<uuid:plan_id>/", views.cart_add, name="cart_add"),
    path("cart/remove/<uuid:plan_id>/", views.cart_remove, name="cart_remove"),
    path("cart/clear/", views.cart_clear, name="cart_clear"),
    path("checkout/", views.checkout, name="checkout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("subscriptions/", views.subscriptions, name="subscriptions"),
    path("orders/", views.orders, name="orders"),
    path("orders/create/<uuid:plan_id>/", views.create_order, name="create_order"),
    path("trial/<slug:slug>/", views.start_trial, name="start_trial"),
]
