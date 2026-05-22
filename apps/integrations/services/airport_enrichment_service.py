from decimal import Decimal, InvalidOperation

from django.db.models import Q

from apps.airports.models import Airport
from .airlabs_service import AirLabsService


class AirportEnrichmentService:
    EMPTY_REASONS = {
        None,
        '',
        '-',
        '--',
        'unknown',
        'n/a',
        'null',
        'none',
    }

    def __init__(self):
        self.client = AirLabsService()

    def _clean_text(self, value):
        if value is None:
            return None

        text = str(value).strip()
        if not text:
            return None

        if text.lower() in self.EMPTY_REASONS:
            return None

        return text

    def _clean_code(self, value):
        value = self._clean_text(value)
        return value.upper() if value else None

    def _normalize_name(self, value):
        value = self._clean_text(value)
        if not value:
            return None

        value = ' '.join(value.split())
        return value

    def _normalize_city(self, value):
        value = self._clean_text(value)
        if not value:
            return None

        value = ' '.join(value.split())
        return value

    def _normalize_country(self, value):
        value = self._clean_text(value)
        if not value:
            return None

        value = ' '.join(value.split())
        return value

    def _parse_decimal(self, value):
        if value in (None, ''):
            return None

        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return None

    def _is_airport_incomplete(self, airport):
        return any([
            not airport.city,
            not airport.country,
            airport.latitude is None,
            airport.longitude is None,
        ])

    def _extract_candidate_from_airlabs(self, payload):
        if not payload:
            return None

        name = self._normalize_name(
            payload.get('name')
            or payload.get('airport_name')
        )

        city = self._normalize_city(
            payload.get('city')
            or payload.get('city_name')
            or payload.get('municipality')
            or payload.get('city_code')
        )

        country = self._normalize_country(
            payload.get('country')
            or payload.get('country_name')
            or payload.get('country_code')
        )

        latitude = self._parse_decimal(
            payload.get('lat')
            or payload.get('latitude')
        )

        longitude = self._parse_decimal(
            payload.get('lng')
            or payload.get('lon')
            or payload.get('longitude')
        )

        iata_code = self._clean_code(
            payload.get('iata_code')
            or payload.get('iata')
        )

        icao_code = self._clean_code(
            payload.get('icao_code')
            or payload.get('icao')
        )

        if not any([
            name,
            city,
            country,
            latitude is not None,
            longitude is not None,
            iata_code,
            icao_code,
        ]):
            return None

        return {
            'name': name,
            'city': city,
            'country': country,
            'latitude': latitude,
            'longitude': longitude,
            'iata_code': iata_code,
            'icao_code': icao_code,
        }

    def _fetch_airport_payload(self, airport):
        payload = None

        if airport.iata_code:
            payload = self.client.get_airport_by_iata(airport.iata_code)

        if not payload and airport.icao_code:
            payload = self.client.get_airport_by_icao(airport.icao_code)

        return payload

    def _should_update_name(self, airport, candidate_name):
        if not candidate_name:
            return False

        current_name = self._normalize_name(airport.name)
        if not current_name:
            return True

        if current_name == candidate_name:
            return False

        current_tokens = set(current_name.lower().replace('-', ' ').split())
        candidate_tokens = set(candidate_name.lower().replace('-', ' ').split())

        if current_tokens == candidate_tokens:
            return False

        return len(candidate_name) > len(current_name)

    def _build_update_plan(self, airport, candidate):
        fields_updated = []

        if self._should_update_name(airport, candidate.get('name')):
            airport.name = candidate['name']
            fields_updated.append('name')

        if not airport.city and candidate.get('city'):
            airport.city = candidate['city']
            fields_updated.append('city')

        if not airport.country and candidate.get('country'):
            airport.country = candidate['country']
            fields_updated.append('country')

        if airport.latitude is None and candidate.get('latitude') is not None:
            airport.latitude = candidate['latitude']
            fields_updated.append('latitude')

        if airport.longitude is None and candidate.get('longitude') is not None:
            airport.longitude = candidate['longitude']
            fields_updated.append('longitude')

        return fields_updated

    def _result(self, airport, updated, reason, fields_updated=None):
        return {
            'airport': airport,
            'updated': updated,
            'reason': reason,
            'fields_updated': fields_updated or [],
        }

    def enrich_airport(self, airport, dry_run=False):
        if not self._is_airport_incomplete(airport):
            return self._result(
                airport=airport,
                updated=False,
                reason='already_complete',
            )

        payload = self._fetch_airport_payload(airport)
        if not payload:
            return self._result(
                airport=airport,
                updated=False,
                reason='no_candidates',
            )

        candidate = self._extract_candidate_from_airlabs(payload)
        if not candidate:
            return self._result(
                airport=airport,
                updated=False,
                reason='no_new_data',
            )

        fields_updated = self._build_update_plan(airport, candidate)
        if not fields_updated:
            return self._result(
                airport=airport,
                updated=False,
                reason='no_new_data',
            )

        if not dry_run:
            airport.save(update_fields=fields_updated + ['updated_at'])

        return self._result(
            airport=airport,
            updated=True,
            reason='enriched',
            fields_updated=fields_updated,
        )

    def enrich_incomplete_airports(self, airport_limit=None, dry_run=False):
        queryset = Airport.objects.filter(
            Q(city='') |
            Q(country='') |
            Q(latitude__isnull=True) |
            Q(longitude__isnull=True)
        ).order_by('name')

        if airport_limit:
            queryset = queryset[:airport_limit]

        stats = {
            'processed': 0,
            'updated': 0,
            'already_complete': 0,
            'no_candidates': 0,
            'no_new_data': 0,
            'errors': 0,
            'details': [],
        }

        for airport in queryset:
            stats['processed'] += 1

            try:
                result = self.enrich_airport(
                    airport=airport,
                    dry_run=dry_run,
                )

                reason = result['reason']

                if result['updated']:
                    stats['updated'] += 1
                elif reason == 'already_complete':
                    stats['already_complete'] += 1
                elif reason == 'no_candidates':
                    stats['no_candidates'] += 1
                elif reason == 'no_new_data':
                    stats['no_new_data'] += 1

                stats['details'].append({
                    'airport': str(airport),
                    'reason': reason,
                    'fields_updated': result['fields_updated'],
                })

            except Exception as exc:
                stats['errors'] += 1
                stats['details'].append({
                    'airport': str(airport),
                    'reason': f'error: {exc}',
                    'fields_updated': [],
                })

        return stats