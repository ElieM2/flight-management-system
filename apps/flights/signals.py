from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Flight, FlightStatusHistory


def _build_change_summary(status_changed, schedule_changed, live_data_changed, previous_status, new_status):
    parts = []

    if status_changed:
        if previous_status:
            parts.append(f"Status changed from {previous_status} to {new_status}")
        else:
            parts.append(f"Initial status set to {new_status}")

    if schedule_changed:
        parts.append("Operational schedule updated")

    if live_data_changed:
        parts.append("Live tracking data updated")

    if not parts:
        parts.append("Flight record updated")

    return " | ".join(parts)


def _get_change_type(status_changed, schedule_changed, live_data_changed, created=False):
    if created:
        return 'created'

    active_flags = [status_changed, schedule_changed, live_data_changed]
    active_count = sum(1 for flag in active_flags if flag)

    if active_count > 1:
        return 'mixed'
    if status_changed:
        return 'status'
    if schedule_changed:
        return 'schedule'
    if live_data_changed:
        return 'live'

    return 'mixed'


@receiver(pre_save, sender=Flight)
def capture_previous_flight_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_state = None
        return

    try:
        instance._previous_state = Flight.objects.get(pk=instance.pk)
    except Flight.DoesNotExist:
        instance._previous_state = None


@receiver(post_save, sender=Flight)
def create_flight_history_entry(sender, instance, created, **kwargs):
    previous = getattr(instance, '_previous_state', None)

    if created:
        FlightStatusHistory.objects.create(
            flight=instance,
            previous_status=None,
            new_status=instance.status,
            change_type='created',
            source_type_snapshot=instance.source_type,
            scheduled_departure_snapshot=instance.scheduled_departure,
            scheduled_arrival_snapshot=instance.scheduled_arrival,
            actual_departure_snapshot=instance.actual_departure,
            actual_arrival_snapshot=instance.actual_arrival,
            departure_delay_minutes=instance.get_departure_delay_minutes(),
            arrival_delay_minutes=instance.get_arrival_delay_minutes(),
            is_disruption_event=instance.has_disruption(),
            status_changed=True,
            schedule_changed=False,
            live_data_changed=False,
            change_summary=f"Initial flight record created with status {instance.status}",
        )
        return

    if not previous:
        return

    status_changed = previous.status != instance.status

    schedule_changed = any([
        previous.scheduled_departure != instance.scheduled_departure,
        previous.scheduled_arrival != instance.scheduled_arrival,
        previous.actual_departure != instance.actual_departure,
        previous.actual_arrival != instance.actual_arrival,
    ])

    live_data_changed = any([
        previous.live_latitude != instance.live_latitude,
        previous.live_longitude != instance.live_longitude,
        previous.live_altitude != instance.live_altitude,
        previous.live_speed != instance.live_speed,
        previous.live_direction != instance.live_direction,
    ])

    source_changed = previous.source_type != instance.source_type

    if not (status_changed or schedule_changed or live_data_changed or source_changed):
        return

    FlightStatusHistory.objects.create(
        flight=instance,
        previous_status=previous.status,
        new_status=instance.status,
        change_type=_get_change_type(
            status_changed=status_changed,
            schedule_changed=schedule_changed or source_changed,
            live_data_changed=live_data_changed,
            created=False
        ),
        source_type_snapshot=instance.source_type,
        scheduled_departure_snapshot=instance.scheduled_departure,
        scheduled_arrival_snapshot=instance.scheduled_arrival,
        actual_departure_snapshot=instance.actual_departure,
        actual_arrival_snapshot=instance.actual_arrival,
        departure_delay_minutes=instance.get_departure_delay_minutes(),
        arrival_delay_minutes=instance.get_arrival_delay_minutes(),
        is_disruption_event=instance.has_disruption(),
        status_changed=status_changed,
        schedule_changed=schedule_changed or source_changed,
        live_data_changed=live_data_changed,
        change_summary=_build_change_summary(
            status_changed=status_changed,
            schedule_changed=schedule_changed or source_changed,
            live_data_changed=live_data_changed,
            previous_status=previous.status,
            new_status=instance.status
        ),
    )