from django.contrib import admin

# Analytics app does not register source-of-truth history models in admin.
# Historical truth is handled by apps.flights.models.FlightStatusHistory.