from django.contrib import admin
from .models import Airline


@admin.register(Airline)
class AirlineAdmin(admin.ModelAdmin):
    list_display = ('name', 'iata_code', 'icao_code', 'country', 'is_active')
    search_fields = ('name', 'iata_code', 'icao_code', 'country')
    list_filter = ('is_active', 'country')