from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.flights.models import Flight
from apps.analytics.models import FlightHistory


def create_history_snapshot(instance, event_type):
    FlightHistory.objects.create(
        flight=instance,
        flight_number=instance.flight_number,
        airline_name=instance.airline.name if instance.airline else 'Unknown',
        origin_iata=instance.origin_airport.iata_code if instance.origin_airport else 'UNK',
        destination_iata=instance.destination_airport.iata_code if instance.destination_airport else 'UNK',
        status=instance.status,
        source_type=instance.source_type,
        scheduled_departure=instance.scheduled_departure,
        scheduled_arrival=instance.scheduled_arrival,
        event_type=event_type,
    )


@receiver(post_save, sender=Flight)
def create_initial_history(sender, instance, created, **kwargs):
    if created:
        create_history_snapshot(instance, 'created')


@receiver(pre_save, sender=Flight)
def track_flight_changes(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        previous = Flight.objects.get(pk=instance.pk)
    except Flight.DoesNotExist:
        return

    if previous.status != instance.status:
        create_history_snapshot(instance, 'status_change')
    elif (
        previous.scheduled_departure != instance.scheduled_departure or
        previous.scheduled_arrival != instance.scheduled_arrival
    ):
        create_history_snapshot(instance, 'schedule_change')
    elif previous.source_type != instance.source_type:
        create_history_snapshot(instance, 'source_change')