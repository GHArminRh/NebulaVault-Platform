from django.urls import path
from . import views

app_name = "portal"
urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.products, name="products"),
    path("products/<slug:slug>/", views.product_detail, name="product_detail"),
    path("pricing/", views.pricing, name="pricing"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("subscriptions/", views.subscriptions, name="subscriptions"),
    path("orders/", views.orders, name="orders"),
    path("orders/create/<int:plan_id>/", views.create_order, name="create_order"),
    path("trial/<slug:slug>/", views.start_trial, name="start_trial"),
    path("register/", views.register, name="register"),
]
