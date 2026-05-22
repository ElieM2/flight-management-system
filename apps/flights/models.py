from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Flight(models.Model):
    FLIGHT_STATUS_CHOICES = [
        ("scheduled", _("Scheduled")),
        ("boarding", _("Boarding")),
        ("departed", _("Departed")),
        ("in_air", _("In Air")),
        ("landed", _("Landed")),
        ("delayed", _("Delayed")),
        ("cancelled", _("Cancelled")),
    ]

    SOURCE_TYPE_CHOICES = [
        ("local", _("Local")),
        ("api", _("API Synced")),
    ]

    flight_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("Flight number"),
    )

    airline = models.ForeignKey(
        "airlines.Airline",
        on_delete=models.CASCADE,
        related_name="flights",
        verbose_name=_("Airline"),
    )

    aircraft = models.ForeignKey(
        "aircraft.Aircraft",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="flights",
        verbose_name=_("Aircraft"),
    )

    origin_airport = models.ForeignKey(
        "airports.Airport",
        on_delete=models.CASCADE,
        related_name="departing_flights",
        verbose_name=_("Origin airport"),
    )

    destination_airport = models.ForeignKey(
        "airports.Airport",
        on_delete=models.CASCADE,
        related_name="arriving_flights",
        verbose_name=_("Destination airport"),
    )

    scheduled_departure = models.DateTimeField(verbose_name=_("Scheduled departure"))
    scheduled_arrival = models.DateTimeField(verbose_name=_("Scheduled arrival"))
    actual_departure = models.DateTimeField(null=True, blank=True, verbose_name=_("Actual departure"))
    actual_arrival = models.DateTimeField(null=True, blank=True, verbose_name=_("Actual arrival"))

    status = models.CharField(
        max_length=20,
        choices=FLIGHT_STATUS_CHOICES,
        default="scheduled",
        db_index=True,
        verbose_name=_("Status"),
    )

    source_type = models.CharField(
        max_length=10,
        choices=SOURCE_TYPE_CHOICES,
        default="local",
        db_index=True,
        verbose_name=_("Source type"),
    )

    external_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_("External ID"),
    )

    live_latitude = models.FloatField(null=True, blank=True, verbose_name=_("Live latitude"))
    live_longitude = models.FloatField(null=True, blank=True, verbose_name=_("Live longitude"))
    live_altitude = models.FloatField(null=True, blank=True, verbose_name=_("Live altitude"))
    live_speed = models.FloatField(null=True, blank=True, verbose_name=_("Live speed"))
    live_direction = models.FloatField(null=True, blank=True, verbose_name=_("Live direction"))

    last_synced_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Last synchronized at"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        ordering = ["-scheduled_departure"]
        verbose_name = _("Flight")
        verbose_name_plural = _("Flights")
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["source_type"]),
            models.Index(fields=["scheduled_departure"]),
            models.Index(fields=["scheduled_arrival"]),
            models.Index(fields=["airline", "status"]),
        ]

    def __str__(self):
        return self.flight_number

    def clean(self):
        errors = {}

        if self.origin_airport_id and self.destination_airport_id:
            if self.origin_airport_id == self.destination_airport_id:
                errors["destination_airport"] = _("Origin and destination airports must be different.")

        if self.scheduled_departure and self.scheduled_arrival:
            if self.scheduled_arrival <= self.scheduled_departure:
                errors["scheduled_arrival"] = _("Scheduled arrival must be after scheduled departure.")

        if self.actual_departure and self.scheduled_departure:
            if self.actual_departure.year < 2000:
                errors["actual_departure"] = _("Actual departure date looks invalid.")

        if self.actual_arrival and self.actual_departure:
            if self.actual_arrival < self.actual_departure:
                errors["actual_arrival"] = _("Actual arrival cannot be earlier than actual departure.")

        if self.live_latitude is not None and not (-90 <= self.live_latitude <= 90):
            errors["live_latitude"] = _("Latitude must be between -90 and 90.")

        if self.live_longitude is not None and not (-180 <= self.live_longitude <= 180):
            errors["live_longitude"] = _("Longitude must be between -180 and 180.")

        if self.live_speed is not None and self.live_speed < 0:
            errors["live_speed"] = _("Live speed cannot be negative.")

        if self.live_altitude is not None and self.live_altitude < 0:
            errors["live_altitude"] = _("Live altitude cannot be negative.")

        if self.live_direction is not None and not (0 <= self.live_direction <= 360):
            errors["live_direction"] = _("Live direction must be between 0 and 360.")

        if errors:
            raise ValidationError(errors)

    @property
    def route(self):
        origin_code = self.origin_airport.iata_code if self.origin_airport else "---"
        destination_code = self.destination_airport.iata_code if self.destination_airport else "---"
        return f"{origin_code} → {destination_code}"

    @property
    def is_active_operation(self):
        return self.status in ["scheduled", "boarding", "departed", "in_air", "delayed"]

    @property
    def is_completed(self):
        return self.status in ["landed", "cancelled"]

    @property
    def is_live_tracked(self):
        return self.live_latitude is not None and self.live_longitude is not None

    @property
    def has_departure_delay(self):
        delay = self.get_departure_delay_minutes()
        return delay is not None and delay > 0

    @property
    def has_arrival_delay(self):
        delay = self.get_arrival_delay_minutes()
        return delay is not None and delay > 0

    @property
    def operational_state_label(self):
        return self.get_status_display()

    def get_departure_delay_minutes(self):
        if self.actual_departure and self.scheduled_departure:
            return int((self.actual_departure - self.scheduled_departure).total_seconds() // 60)
        return None

    def get_arrival_delay_minutes(self):
        if self.actual_arrival and self.scheduled_arrival:
            return int((self.actual_arrival - self.scheduled_arrival).total_seconds() // 60)
        return None

    def has_disruption(self):
        return self.status in ["delayed", "cancelled"]

    def mark_synced(self):
        self.last_synced_at = timezone.now()


class FlightStatusHistory(models.Model):
    CHANGE_TYPE_CHOICES = [
        ("created", _("Created")),
        ("status", _("Status Change")),
        ("schedule", _("Schedule Change")),
        ("live", _("Live Data Change")),
        ("mixed", _("Mixed Change")),
    ]

    flight = models.ForeignKey(
        Flight,
        on_delete=models.CASCADE,
        related_name="status_history",
        verbose_name=_("Flight"),
    )

    previous_status = models.CharField(
        max_length=20,
        choices=Flight.FLIGHT_STATUS_CHOICES,
        null=True,
        blank=True,
        verbose_name=_("Previous status"),
    )

    new_status = models.CharField(
        max_length=20,
        choices=Flight.FLIGHT_STATUS_CHOICES,
        verbose_name=_("New status"),
    )

    change_type = models.CharField(
        max_length=20,
        choices=CHANGE_TYPE_CHOICES,
        default="status",
        verbose_name=_("Change type"),
    )

    source_type_snapshot = models.CharField(
        max_length=10,
        choices=Flight.SOURCE_TYPE_CHOICES,
        default="local",
        verbose_name=_("Source type snapshot"),
    )

    scheduled_departure_snapshot = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Scheduled departure snapshot"),
    )
    scheduled_arrival_snapshot = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Scheduled arrival snapshot"),
    )
    actual_departure_snapshot = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Actual departure snapshot"),
    )
    actual_arrival_snapshot = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Actual arrival snapshot"),
    )

    departure_delay_minutes = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Departure delay minutes"),
    )
    arrival_delay_minutes = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Arrival delay minutes"),
    )

    is_disruption_event = models.BooleanField(default=False, verbose_name=_("Disruption event"))
    status_changed = models.BooleanField(default=False, verbose_name=_("Status changed"))
    schedule_changed = models.BooleanField(default=False, verbose_name=_("Schedule changed"))
    live_data_changed = models.BooleanField(default=False, verbose_name=_("Live data changed"))

    change_summary = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Change summary"),
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="flight_history_entries",
        verbose_name=_("Changed by"),
    )

    changed_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Changed at"))

    class Meta:
        ordering = ["-changed_at"]
        verbose_name = _("Flight Status History")
        verbose_name_plural = _("Flight Status History")
        indexes = [
            models.Index(fields=["flight", "-changed_at"]),
            models.Index(fields=["new_status"]),
            models.Index(fields=["change_type"]),
        ]

    def __str__(self):
        return f"{self.flight.flight_number} - {self.new_status} - {self.changed_at:%Y-%m-%d %H:%M}"