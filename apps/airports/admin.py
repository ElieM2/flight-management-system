from django.contrib import admin
from .models import Airport


@admin.register(Airport)
class AirportAdmin(admin.ModelAdmin):
    list_display = ('name', 'iata_code', 'icao_code', 'city', 'country', 'is_active')
    search_fields = ('name', 'iata_code', 'icao_code', 'city', 'country')
    list_filter = ('is_active', 'country')