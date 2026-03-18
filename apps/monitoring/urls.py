from django.urls import path
from .views import monitoring_home, map_view

urlpatterns = [
    path('', monitoring_home, name='monitoring_home'),
    path('map/', map_view, name='map_view'),
]