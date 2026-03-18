from django.contrib import admin
from .models import Flight


@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = (
        'flight_number',
        'airline',
        'origin_airport',
        'destination_airport',
        'scheduled_departure',
        'status',
        'source_type',
    )
    search_fields = ('flight_number',)
    list_filter = ('status', 'source_type', 'airline')