from django.db import models


class Flight(models.Model):
    FLIGHT_STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('boarding', 'Boarding'),
        ('departed', 'Departed'),
        ('in_air', 'In Air'),
        ('landed', 'Landed'),
        ('delayed', 'Delayed'),
        ('cancelled', 'Cancelled'),
    ]

    SOURCE_TYPE_CHOICES = [
        ('local', 'Local'),
        ('api', 'API Synced'),
    ]

    flight_number = models.CharField(max_length=20, unique=True)
    airline = models.ForeignKey(
        'airlines.Airline',
        on_delete=models.CASCADE,
        related_name='flights'
    )
    aircraft = models.ForeignKey(
        'aircraft.Aircraft',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='flights'
    )
    origin_airport = models.ForeignKey(
        'airports.Airport',
        on_delete=models.CASCADE,
        related_name='departing_flights'
    )
    destination_airport = models.ForeignKey(
        'airports.Airport',
        on_delete=models.CASCADE,
        related_name='arriving_flights'
    )
    scheduled_departure = models.DateTimeField()
    scheduled_arrival = models.DateTimeField()
    actual_departure = models.DateTimeField(null=True, blank=True)
    actual_arrival = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=FLIGHT_STATUS_CHOICES,
        default='scheduled'
    )
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPE_CHOICES,
        default='local'
    )
    external_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_departure']
        verbose_name = 'Flight'
        verbose_name_plural = 'Flights'

    def __str__(self):
        return self.flight_number