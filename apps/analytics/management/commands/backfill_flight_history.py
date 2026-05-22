from django.core.management.base import BaseCommand

from apps.flights.models import Flight
from apps.analytics.models import FlightHistory


class Command(BaseCommand):
    help = "Create baseline historical records for existing flights"

    def handle(self, *args, **options):
        created_count = 0

        for flight in Flight.objects.select_related('airline', 'origin_airport', 'destination_airport'):
            exists = FlightHistory.objects.filter(
                flight=flight,
                event_type='created'
            ).exists()

            if not exists:
                FlightHistory.objects.create(
                    flight=flight,
                    flight_number=flight.flight_number,
                    airline_name=flight.airline.name if flight.airline else 'Unknown',
                    origin_iata=flight.origin_airport.iata_code if flight.origin_airport else 'UNK',
                    destination_iata=flight.destination_airport.iata_code if flight.destination_airport else 'UNK',
                    status=flight.status,
                    source_type=flight.source_type,
                    scheduled_departure=flight.scheduled_departure,
                    scheduled_arrival=flight.scheduled_arrival,
                    event_type='created',
                )
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Backfill completed. {created_count} history record(s) created.'
        ))