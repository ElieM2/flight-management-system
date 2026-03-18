from django.urls import path
from .views import aircraft_list

urlpatterns = [
    path('', aircraft_list, name='aircraft_list'),
]