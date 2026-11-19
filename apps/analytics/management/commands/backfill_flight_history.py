from django.core.management.base import BaseCommand

from apps.flights.models import Flight, FlightStatusHistory


class Command(BaseCommand):
    help = "Create baseline historical records for existing flights"

    def handle(self, *args, **options):
        created_count = 0

        flights = Flight.objects.select_related(
            "airline",
            "origin_airport",
            "destination_airport",
        )

        for flight in flights:
            exists = FlightStatusHistory.objects.filter(
                flight=flight,
                change_type="created",
            ).exists()

            if exists:
                continue

            FlightStatusHistory.objects.create(
                flight=flight,
                previous_status=None,
                new_status=flight.status,
                change_type="created",
                source_type_snapshot=flight.source_type,
                scheduled_departure_snapshot=flight.scheduled_departure,
                scheduled_arrival_snapshot=flight.scheduled_arrival,
                actual_departure_snapshot=flight.actual_departure,
                actual_arrival_snapshot=flight.actual_arrival,
                departure_delay_minutes=flight.get_departure_delay_minutes(),
                arrival_delay_minutes=flight.get_arrival_delay_minutes(),
                is_disruption_event=flight.has_disruption(),
                status_changed=True,
                schedule_changed=False,
                live_data_changed=False,
                change_summary=(
                    f"Initial flight record created with status {flight.status}"
                ),
            )
            created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Backfill completed. {created_count} history record(s) created."
        ))
