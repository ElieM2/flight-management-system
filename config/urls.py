from django.contrib import admin
from django.urls import path, include
from apps.monitoring.views import map_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.dashboard.urls')),
    path('flights/', include('apps.flights.urls')),
    path('airlines/', include('apps.airlines.urls')),
    path('airports/', include('apps.airports.urls')),
    path('aircraft/', include('apps.aircraft.urls')),
    path('monitoring/', include('apps.monitoring.urls')),
    path('map/', map_view, name='map_view'),
    path('sync/', include('apps.integrations.urls')),
]