from django.urls import path

from .views import flight_detail, flight_list


app_name = "flights"

urlpatterns = [
    path("", flight_list, name="flight_list"),
    path("<int:pk>/", flight_detail, name="flight_detail"),
]