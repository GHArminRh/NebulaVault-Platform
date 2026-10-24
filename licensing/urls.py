from django.urls import path

from . import views

app_name = "licensing"

urlpatterns = [
    path("activate/", views.activate, name="activate"),
    path("validate/", views.validate, name="validate"),
    path("deactivate/", views.deactivate, name="deactivate"),
]
