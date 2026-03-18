from django.core.management.base import BaseCommand
from apps.integrations.services.sync_service import FlightSyncService


class Command(BaseCommand):
    help = 'Synchronize flights from aviationstack API'

    def add_arguments(self, parser):
        parser.add_argument('--flight_iata', type=str, help='Flight IATA code')
        parser.add_argument('--dep_iata', type=str, help='Departure airport IATA code')
        parser.add_argument('--arr_iata', type=str, help='Arrival airport IATA code')
        parser.add_argument('--limit', type=int, default=20, help='Number of records to fetch')

    def handle(self, *args, **options):
        service = FlightSyncService()

        result = service.sync_flights(
            flight_iata=options.get('flight_iata'),
            dep_iata=options.get('dep_iata'),
            arr_iata=options.get('arr_iata'),
            limit=options.get('limit'),
        )

        self.stdout.write(self.style.SUCCESS(
            f"Sync completed - received: {result['received']}, "
            f"created: {result['created']}, updated: {result['updated']}"
        ))