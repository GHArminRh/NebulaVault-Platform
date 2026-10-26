from django.urls import path
from . import simulator, views

app_name = "billing"
urlpatterns = [
    path("zarinpal/start/<uuid:plan_id>/", views.start_zarinpal_payment, name="zarinpal_start"),
    path("zarinpal/callback/", views.zarinpal_callback, name="zarinpal_callback"),
    path("test/start/<uuid:plan_id>/", simulator.start_local_simulation, name="local_simulator_start"),
    path("test/simulator/<uuid:attempt_id>/", simulator.local_simulator, name="local_simulator"),
    path("test/simulator/<uuid:attempt_id>/complete/", simulator.complete_local_simulation, name="local_simulator_complete"),
]
