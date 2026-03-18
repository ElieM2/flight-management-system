from django.urls import path
from .views import airline_list

urlpatterns = [
    path('', airline_list, name='airline_list'),
]