from datetime import datetime, timezone as dt_timezone
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from apps.airlines.models import Airline
from apps.airports.models import Airport
from apps.flights.models import Flight
from apps.integrations.models import ApiSyncLog
from .aviationstack_service import AviationstackService


class FlightSyncService:
    PROVIDER_NAME = 'aviationstack'

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

    def _clean_text(self, value):
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    def _clean_code(self, value):
        value = self._clean_text(value)
        return value.upper() if value else None

    def _parse_datetime(self, value):
        if not value:
            return None

        try:
            dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except Exception:
            return None

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=dt_timezone.utc)

        return dt

    def _parse_decimal(self, value, default=None):
        if value in (None, ''):
            return default

        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return default

    def _parse_coordinate(self, value):
        return self._parse_decimal(value, default=None)

    def _has_meaningful_coordinate(self, value):
        return value is not None

    def _map_status(self, api_status):
        if not api_status:
            return 'scheduled'
        return self.STATUS_MAPPING.get(str(api_status).lower(), 'scheduled')

    def _build_snapshot(self, flight):
        if not flight:
            return None

        return {
            'status': flight.status,
            'source_type': flight.source_type,
            'scheduled_departure': flight.scheduled_departure,
            'scheduled_arrival': flight.scheduled_arrival,
            'actual_departure': flight.actual_departure,
            'actual_arrival': flight.actual_arrival,
            'live_latitude': flight.live_latitude,
            'live_longitude': flight.live_longitude,
            'live_altitude': flight.live_altitude,
            'live_speed': flight.live_speed,
            'live_direction': flight.live_direction,
            'external_id': flight.external_id,
        }

    def _will_generate_history(self, previous_snapshot, current_values, created):
        if created or not previous_snapshot:
            return True

        return any([
            previous_snapshot['status'] != current_values['status'],
            previous_snapshot['source_type'] != current_values['source_type'],
            previous_snapshot['scheduled_departure'] != current_values['scheduled_departure'],
            previous_snapshot['scheduled_arrival'] != current_values['scheduled_arrival'],
            previous_snapshot['actual_departure'] != current_values['actual_departure'],
            previous_snapshot['actual_arrival'] != current_values['actual_arrival'],
            previous_snapshot['live_latitude'] != current_values['live_latitude'],
            previous_snapshot['live_longitude'] != current_values['live_longitude'],
            previous_snapshot['live_altitude'] != current_values['live_altitude'],
            previous_snapshot['live_speed'] != current_values['live_speed'],
            previous_snapshot['live_direction'] != current_values['live_direction'],
            previous_snapshot['external_id'] != current_values['external_id'],
        ])

    def _get_or_create_airline(self, airline_name, airline_iata, airline_icao):
        airline_name = self._clean_text(airline_name)
        airline_iata = self._clean_code(airline_iata)
        airline_icao = self._clean_code(airline_icao)

        airline = None

        if airline_iata:
            airline = Airline.objects.filter(iata_code=airline_iata).first()

        if not airline and airline_icao:
            airline = Airline.objects.filter(icao_code=airline_icao).first()

        if not airline and airline_name:
            airline = Airline.objects.filter(name=airline_name).first()

        if airline:
            changed = False
            update_fields = []

            if airline_name and airline.name != airline_name:
                airline.name = airline_name
                changed = True
                update_fields.append('name')

            if airline_iata and airline.iata_code != airline_iata:
                airline.iata_code = airline_iata
                changed = True
                update_fields.append('iata_code')

            if airline_icao and airline.icao_code != airline_icao:
                airline.icao_code = airline_icao
                changed = True
                update_fields.append('icao_code')

            if changed:
                airline.save(update_fields=update_fields)

            return airline

        if not (airline_name and airline_iata and airline_icao):
            return None

        return Airline.objects.create(
            name=airline_name,
            iata_code=airline_iata,
            icao_code=airline_icao,
            country='',
            is_active=True,
        )

    def _get_or_create_airport(
        self,
        airport_name,
        iata_code,
        icao_code,
        city=None,
        country=None,
        latitude=None,
        longitude=None,
    ):
        airport_name = self._clean_text(airport_name)
        iata_code = self._clean_code(iata_code)
        icao_code = self._clean_code(icao_code)
        city = self._clean_text(city)
        country = self._clean_text(country)
        latitude = self._parse_coordinate(latitude)
        longitude = self._parse_coordinate(longitude)

        airport = None

        if iata_code:
            airport = Airport.objects.filter(iata_code=iata_code).first()

        if not airport and icao_code:
            airport = Airport.objects.filter(icao_code=icao_code).first()

        if airport:
            changed = False
            update_fields = []

            if airport_name and airport.name != airport_name:
                airport.name = airport_name
                changed = True
                update_fields.append('name')

            if iata_code and airport.iata_code != iata_code:
                airport.iata_code = iata_code
                changed = True
                update_fields.append('iata_code')

            if icao_code and airport.icao_code != icao_code:
                airport.icao_code = icao_code
                changed = True
                update_fields.append('icao_code')

            if city and airport.city != city:
                airport.city = city
                changed = True
                update_fields.append('city')

            if country and airport.country != country:
                airport.country = country
                changed = True
                update_fields.append('country')

            if self._has_meaningful_coordinate(latitude) and airport.latitude != latitude:
                airport.latitude = latitude
                changed = True
                update_fields.append('latitude')

            if self._has_meaningful_coordinate(longitude) and airport.longitude != longitude:
                airport.longitude = longitude
                changed = True
                update_fields.append('longitude')

            if changed:
                airport.save(update_fields=update_fields)

            return airport

        if not (airport_name and iata_code and icao_code):
            return None

        return Airport.objects.create(
            name=airport_name,
            iata_code=iata_code,
            icao_code=icao_code,
            city=city or '',
            country=country or '',
            latitude=latitude,
            longitude=longitude,
            is_active=True,
        )

    def sync_flights(self, flight_iata=None, dep_iata=None, arr_iata=None, limit=20):
        started_at = timezone.now()

        log = ApiSyncLog.objects.create(
            provider_name=self.PROVIDER_NAME,
            sync_type='flights',
            started_at=started_at,
            status='failed',
            records_received=0,
            records_created=0,
            records_updated=0,
            message='Sync started',
        )

        created_count = 0
        updated_count = 0
        skipped_local_count = 0
        skipped_incomplete_count = 0
        history_created_count = 0

        try:
            payload = self.client.get_flights(
                flight_iata=flight_iata,
                dep_iata=dep_iata,
                arr_iata=arr_iata,
                limit=limit,
            )

            flights_data = payload.get('data', [])
            log.records_received = len(flights_data)

            for item in flights_data:
                airline_data = item.get('airline') or {}
                departure_data = item.get('departure') or {}
                arrival_data = item.get('arrival') or {}
                flight_data = item.get('flight') or {}
                live_data = item.get('live') or {}

                airline_name = airline_data.get('name')
                airline_iata = airline_data.get('iata')
                airline_icao = airline_data.get('icao')

                dep_airport_name = departure_data.get('airport')
                dep_iata_code = departure_data.get('iata')
                dep_icao_code = departure_data.get('icao')

                arr_airport_name = arrival_data.get('airport')
                arr_iata_code = arrival_data.get('iata')
                arr_icao_code = arrival_data.get('icao')

                flight_number = self._clean_text(
                    flight_data.get('iata') or flight_data.get('icao')
                )
                api_status = item.get('flight_status')

                scheduled_departure = self._parse_datetime(departure_data.get('scheduled'))
                scheduled_arrival = self._parse_datetime(arrival_data.get('scheduled'))
                actual_departure = self._parse_datetime(departure_data.get('actual'))
                actual_arrival = self._parse_datetime(arrival_data.get('actual'))

                if not all([
                    flight_number,
                    scheduled_departure,
                    scheduled_arrival,
                    airline_name,
                    dep_airport_name,
                    arr_airport_name,
                ]):
                    skipped_incomplete_count += 1
                    continue

                airline = self._get_or_create_airline(
                    airline_name=airline_name,
                    airline_iata=airline_iata,
                    airline_icao=airline_icao,
                )

                origin_airport = self._get_or_create_airport(
                    airport_name=dep_airport_name,
                    iata_code=dep_iata_code,
                    icao_code=dep_icao_code,
                    city=departure_data.get('city'),
                    country=departure_data.get('country'),
                    latitude=departure_data.get('latitude'),
                    longitude=departure_data.get('longitude'),
                )

                destination_airport = self._get_or_create_airport(
                    airport_name=arr_airport_name,
                    iata_code=arr_iata_code,
                    icao_code=arr_icao_code,
                    city=arrival_data.get('city'),
                    country=arrival_data.get('country'),
                    latitude=arrival_data.get('latitude'),
                    longitude=arrival_data.get('longitude'),
                )

                if not airline or not origin_airport or not destination_airport:
                    skipped_incomplete_count += 1
                    continue

                existing_flight = Flight.objects.filter(flight_number=flight_number).first()

                if existing_flight and existing_flight.source_type == 'local':
                    skipped_local_count += 1
                    continue

                previous_snapshot = self._build_snapshot(existing_flight)

                defaults = {
                    'airline': airline,
                    'origin_airport': origin_airport,
                    'destination_airport': destination_airport,
                    'scheduled_departure': scheduled_departure,
                    'scheduled_arrival': scheduled_arrival,
                    'actual_departure': actual_departure,
                    'actual_arrival': actual_arrival,
                    'status': self._map_status(api_status),
                    'source_type': 'api',
                    'external_id': self._clean_text(
                        item.get('flight_date')
                        or live_data.get('updated')
                        or flight_data.get('number')
                    ),
                    'live_latitude': live_data.get('latitude'),
                    'live_longitude': live_data.get('longitude'),
                    'live_altitude': live_data.get('altitude'),
                    'live_speed': live_data.get('speed_horizontal'),
                    'live_direction': live_data.get('direction'),
                }

                with transaction.atomic():
                    flight_obj, created = Flight.objects.update_or_create(
                        flight_number=flight_number,
                        defaults=defaults,
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                    current_values = {
                        'status': flight_obj.status,
                        'source_type': flight_obj.source_type,
                        'scheduled_departure': flight_obj.scheduled_departure,
                        'scheduled_arrival': flight_obj.scheduled_arrival,
                        'actual_departure': flight_obj.actual_departure,
                        'actual_arrival': flight_obj.actual_arrival,
                        'live_latitude': flight_obj.live_latitude,
                        'live_longitude': flight_obj.live_longitude,
                        'live_altitude': flight_obj.live_altitude,
                        'live_speed': flight_obj.live_speed,
                        'live_direction': flight_obj.live_direction,
                        'external_id': flight_obj.external_id,
                    }

                    if self._will_generate_history(
                        previous_snapshot=previous_snapshot,
                        current_values=current_values,
                        created=created,
                    ):
                        history_created_count += 1

            log.status = 'success'
            log.records_created = created_count
            log.records_updated = updated_count
            log.message = (
                f"Sync completed successfully. "
                f"Created: {created_count}, Updated: {updated_count}, "
                f"History via signals: {history_created_count}, "
                f"Skipped local: {skipped_local_count}, "
                f"Skipped incomplete: {skipped_incomplete_count}"
            )
            log.finished_at = timezone.now()
            log.save()

            return {
                'received': len(flights_data),
                'created': created_count,
                'updated': updated_count,
                'history_created': history_created_count,
                'skipped_local': skipped_local_count,
                'skipped_incomplete': skipped_incomplete_count,
            }

        except Exception as e:
            log.status = 'failed'
            log.message = (
                str(e).replace(self.client.api_key, '***REDACTED_API_KEY***')
                if getattr(self.client, 'api_key', None)
                else str(e)
            )
            log.finished_at = timezone.now()
            log.save()
            raise