from django.urls import path

from . import views

app_name = "blog"
urlpatterns = [
    path("", views.post_list, name="post_list"),
    path("tag/<uuid:tag_id>/", views.tag_list, name="tag_list"),
    path("<slug:slug>/rate/", views.rate_post, name="rate_post"),
    path("<slug:slug>/", views.post_detail, name="post_detail"),
]
