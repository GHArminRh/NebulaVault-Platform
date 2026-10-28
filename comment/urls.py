from django.urls import path
from . import views
app_name="comment"
urlpatterns=[
 path("create/",views.create,name="create"),
 path("<int:pk>/edit/",views.edit,name="edit"),
 path("<int:pk>/delete/",views.delete,name="delete"),
 path("<int:pk>/react/",views.react,name="react"),
]
