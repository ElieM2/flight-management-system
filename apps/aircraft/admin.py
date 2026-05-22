from django.contrib import admin

from .models import Aircraft


@admin.register(Aircraft)
class AircraftAdmin(admin.ModelAdmin):
    list_display = (
        "registration_number",
        "model",
        "aircraft_type",
        "airline",
        "capacity",
        "status",
    )
    search_fields = (
        "registration_number",
        "model",
        "aircraft_type",
        "airline__name",
    )
    list_filter = (
        "status",
        "airline",
    )