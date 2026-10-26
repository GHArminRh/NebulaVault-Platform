from django.urls import path
from . import zarinpal_views

app_name = "billing"
urlpatterns = [
    path("zarinpal/start/<uuid:order_id>/", zarinpal_views.zarinpal_start, name="zarinpal_start"),
    path("zarinpal/callback/", zarinpal_views.zarinpal_callback, name="zarinpal_callback"),
]
