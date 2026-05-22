import time
from django.core.management.base import BaseCommand
from apps.integrations.services.sync_service import FlightSyncService


class Command(BaseCommand):
    help = 'Automatically sync flights from Aviationstack every X seconds'

    def add_arguments(self, parser):
        parser.add_argument('--dep_iata', type=str, default=None)
        parser.add_argument('--arr_iata', type=str, default=None)
        parser.add_argument('--flight_iata', type=str, default=None)
        parser.add_argument('--limit', type=int, default=10)
        parser.add_argument('--interval', type=int, default=300)

    def handle(self, *args, **options):
        service = FlightSyncService()

        dep_iata = options['dep_iata']
        arr_iata = options['arr_iata']
        flight_iata = options['flight_iata']
        limit = options['limit']
        interval = options['interval']

        self.stdout.write(self.style.SUCCESS('Auto sync started...'))

        while True:
            try:
                result = service.sync_flights(
                    flight_iata=flight_iata,
                    dep_iata=dep_iata,
                    arr_iata=arr_iata,
                    limit=limit
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Received: {result['received']} | "
                        f"Created: {result['created']} | "
                        f"Updated: {result['updated']} | "
                        f"Skipped local: {result['skipped_local']}"
                    )
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Sync error: {e}"))

            time.sleep(interval)