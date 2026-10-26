from django.urls import path
from . import views

app_name = "billing"
urlpatterns = [
    path("zarinpal/start/<uuid:plan_id>/", views.start_zarinpal_payment, name="zarinpal_start"),
    path("zarinpal/cart/", views.start_zarinpal_cart_payment, name="zarinpal_cart_start"),
    path("zarinpal/callback/", views.zarinpal_callback, name="zarinpal_callback"),
    path("orders/<uuid:order_number>/pay/", views.pay_existing_order, name="order_pay"),
]
