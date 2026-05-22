from django.urls import path
from . import views

app_name = "aircraft"

urlpatterns = [
    path("", views.aircraft_list, name="aircraft_list"),
    path("<int:pk>/", views.aircraft_detail, name="aircraft_detail"),
]