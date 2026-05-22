from django.urls import path

from .views import (
    map_view,
    monitoring_alerts_view,
    monitoring_critical_view,
    monitoring_flight_detail_view,
    monitoring_home,
    monitoring_live_view,
    weather_hazards_api,
)

app_name = 'monitoring'

urlpatterns = [
    path('', monitoring_home, name='monitoring_home'),
    path('map/', map_view, name='flight_map'),

    path('api/weather-hazards/', weather_hazards_api, name='weather_hazards_api'),

    path('alerts/', monitoring_alerts_view, name='monitoring_alerts'),
    path('critical/', monitoring_critical_view, name='monitoring_critical'),
    path('live/', monitoring_live_view, name='monitoring_live'),
    path('flight/<int:pk>/', monitoring_flight_detail_view, name='monitoring_flight_detail'),
]