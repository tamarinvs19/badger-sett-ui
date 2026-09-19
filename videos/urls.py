from django.urls import path

from . import views

app_name = "videos"

urlpatterns = [
    path("health/", views.health, name="health"),
    path("", views.VideoListView.as_view(), name="list"),
    path("video/<int:pk>/", views.VideoDetailView.as_view(), name="detail"),
]