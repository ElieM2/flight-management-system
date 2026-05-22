from django.db import models

# This app does not define source-of-truth historical models.
# Historical truth is stored in apps.flights.models.FlightStatusHistory.
# The analytics app is reserved for analytical services, scoring, and interpretation.