from datetime import datetime
from django.utils import timezone

from apps.airlines.models import Airline
from apps.airports.models import Airport
from apps.flights.models import Flight
from apps.integrations.models import ApiSyncLog
from .aviationstack_service import AviationstackService


class FlightSyncService:
    STATUS_MAPPING = {
        'scheduled': 'scheduled',
        'active': 'in_air',
        'landed': 'landed',
        'cancelled': 'cancelled',
        'incident': 'delayed',
        'diverted': 'delayed',
    }

    def __init__(self):
        self.client = AviationstackService()

    def _parse_datetime(self, value):
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt
        except Exception:
            return None

    def _map_status(self, api_status):
        if not api_status:
            return 'scheduled'
        return self.STATUS_MAPPING.get(api_status.lower(), 'scheduled')

    def sync_flights(self, flight_iata=None, dep_iata=None, arr_iata=None, limit=20):
        started_at = timezone.now()

        log = ApiSyncLog.objects.create(
            provider_name='aviationstack',
            sync_type='flights',
            started_at=started_at,
            status='failed',
            records_received=0,
            records_created=0,
            records_updated=0,
            message='Sync started'
        )

        created_count = 0
        updated_count = 0

        try:
            payload = self.client.get_flights(
                flight_iata=flight_iata,
                dep_iata=dep_iata,
                arr_iata=arr_iata,
                limit=limit
            )

            flights_data = payload.get('data', [])
            log.records_received = len(flights_data)

            for item in flights_data:
                airline_data = item.get('airline') or {}
                departure_data = item.get('departure') or {}
                arrival_data = item.get('arrival') or {}
                flight_data = item.get('flight') or {}

                airline_name = airline_data.get('name')
                airline_iata = airline_data.get('iata') or 'NA'
                airline_icao = airline_data.get('icao') or 'N/A'

                dep_airport_name = departure_data.get('airport')
                dep_iata_code = departure_data.get('iata') or 'XXX'
                dep_icao_code = departure_data.get('icao') or f"DEP{dep_iata_code}"

                arr_airport_name = arrival_data.get('airport')
                arr_iata_code = arrival_data.get('iata') or 'YYY'
                arr_icao_code = arrival_data.get('icao') or f"ARR{arr_iata_code}"

                flight_number = flight_data.get('iata') or flight_data.get('icao')
                api_status = item.get('flight_status')

                scheduled_departure = self._parse_datetime(departure_data.get('scheduled'))
                scheduled_arrival = self._parse_datetime(arrival_data.get('scheduled'))
                actual_departure = self._parse_datetime(departure_data.get('actual'))
                actual_arrival = self._parse_datetime(arrival_data.get('actual'))

                if not all([
                    airline_name,
                    dep_airport_name,
                    arr_airport_name,
                    flight_number,
                    scheduled_departure,
                    scheduled_arrival,
                ]):
                    continue

                airline, _ = Airline.objects.get_or_create(
                    iata_code=airline_iata,
                    defaults={
                        'name': airline_name,
                        'icao_code': airline_icao[:3],
                        'country': 'Unknown',
                        'is_active': True,
                    }
                )

                if airline.name != airline_name:
                    airline.name = airline_name
                    airline.save()

                origin_airport, _ = Airport.objects.get_or_create(
                    iata_code=dep_iata_code,
                    defaults={
                        'name': dep_airport_name,
                        'icao_code': dep_icao_code[:4],
                        'city': 'Unknown',
                        'country': 'Unknown',
                        'latitude': 0.0,
                        'longitude': 0.0,
                        'is_active': True,
                    }
                )

                destination_airport, _ = Airport.objects.get_or_create(
                    iata_code=arr_iata_code,
                    defaults={
                        'name': arr_airport_name,
                        'icao_code': arr_icao_code[:4],
                        'city': 'Unknown',
                        'country': 'Unknown',
                        'latitude': 0.0,
                        'longitude': 0.0,
                        'is_active': True,
                    }
                )

                flight_obj, created = Flight.objects.update_or_create(
                    flight_number=flight_number,
                    defaults={
                        'airline': airline,
                        'origin_airport': origin_airport,
                        'destination_airport': destination_airport,
                        'scheduled_departure': scheduled_departure,
                        'scheduled_arrival': scheduled_arrival,
                        'actual_departure': actual_departure,
                        'actual_arrival': actual_arrival,
                        'status': self._map_status(api_status),
                        'source_type': 'api',
                        'external_id': str(item.get('live', {}).get('updated')) if item.get('live') else None,
                    }
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            log.status = 'success'
            log.records_created = created_count
            log.records_updated = updated_count
            log.message = 'Sync completed successfully'
            log.finished_at = timezone.now()
            log.save()

            return {
                'received': len(flights_data),
                'created': created_count,
                'updated': updated_count,
            }

        except Exception as e:
            log.status = 'failed'
            log.message = str(e)
            log.finished_at = timezone.now()
            log.save()
            raise