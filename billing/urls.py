from django.urls import path

from . import views

app_name = "billing"
urlpatterns = [
    path("zarinpal/start/<uuid:order_id>/", views.zarinpal_start, name="zarinpal_start"),
    path("zarinpal/callback/", views.zarinpal_callback, name="zarinpal_callback"),
]
