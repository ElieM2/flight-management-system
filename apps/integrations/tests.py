import os
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.cache import cache
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.airlines.models import Airline
from apps.airports.models import Airport
from apps.flights.models import Flight
from apps.integrations import views
from apps.integrations.models import ApiSyncLog
from apps.integrations.services.aviationstack_service import AviationstackService
from apps.integrations.services.sync_service import FlightSyncService
from apps.integrations.services.weather_service import (
    AirportWeatherPoint,
    WeatherHazardService,
)


class FakeResponse:
    def __init__(self, payload=None, status_code=200, json_error=None, http_error=False):
        self.payload = payload or {}
        self.status_code = status_code
        self.json_error = json_error
        self.http_error = http_error

    def raise_for_status(self):
        if self.http_error:
            error = requests.HTTPError(
                f"{self.status_code} Error for url with access_key=SECRET_KEY"
            )
            error.response = self
            raise error

    def json(self):
        if self.json_error:
            raise ValueError(self.json_error)

        return self.payload


class AviationstackServiceTests(TestCase):
    def test_missing_api_key_raises_clear_runtime_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as context:
                AviationstackService()

        self.assertIn("AVIATIONSTACK_API_KEY", str(context.exception))

    def test_service_initializes_with_environment_configuration(self):
        with patch.dict(
            os.environ,
            {
                "AVIATIONSTACK_API_KEY": "SECRET_KEY",
                "AVIATIONSTACK_BASE_URL": "https://example.test/v1/",
            },
            clear=True,
        ):
            service = AviationstackService()

        self.assertEqual(service.api_key, "SECRET_KEY")
        self.assertEqual(service.base_url, "https://example.test/v1")

    def test_sanitize_text_removes_plain_key_and_access_key_parameter(self):
        with patch.dict(os.environ, {"AVIATIONSTACK_API_KEY": "SECRET_KEY"}, clear=True):
            service = AviationstackService()

        text = "Request failed with SECRET_KEY and access_key=ANOTHER_SECRET&limit=10"
        sanitized = service._sanitize_text(text)

        self.assertNotIn("SECRET_KEY", sanitized)
        self.assertNotIn("ANOTHER_SECRET", sanitized)
        self.assertIn("***REDACTED_API_KEY***", sanitized)

    def test_get_flights_returns_payload_when_provider_response_is_valid(self):
        with patch.dict(os.environ, {"AVIATIONSTACK_API_KEY": "SECRET_KEY"}, clear=True):
            service = AviationstackService()

        service.session = Mock()
        service.session.get.return_value = FakeResponse(
            payload={
                "data": [
                    {
                        "flight_status": "active",
                        "flight": {"iata": "AA100"},
                    }
                ]
            }
        )

        payload = service.get_flights(
            flight_iata="AA100",
            dep_iata="MSQ",
            arr_iata="CDG",
            limit=5,
        )

        self.assertIn("data", payload)
        self.assertEqual(payload["data"][0]["flight"]["iata"], "AA100")

        service.session.get.assert_called_once()
        call_args = service.session.get.call_args

        self.assertEqual(call_args.args[0], "https://api.aviationstack.com/v1/flights")
        self.assertEqual(call_args.kwargs["params"]["access_key"], "SECRET_KEY")
        self.assertEqual(call_args.kwargs["params"]["flight_iata"], "AA100")
        self.assertEqual(call_args.kwargs["params"]["dep_iata"], "MSQ")
        self.assertEqual(call_args.kwargs["params"]["arr_iata"], "CDG")
        self.assertEqual(call_args.kwargs["params"]["limit"], 5)

    def test_get_flights_maps_http_401_to_authentication_error(self):
        with patch.dict(os.environ, {"AVIATIONSTACK_API_KEY": "SECRET_KEY"}, clear=True):
            service = AviationstackService()

        service.session = Mock()
        service.session.get.return_value = FakeResponse(status_code=401, http_error=True)

        with self.assertRaises(RuntimeError) as context:
            service.get_flights()

        self.assertIn("authentication failed", str(context.exception).lower())

    def test_get_flights_maps_http_403_to_access_error(self):
        with patch.dict(os.environ, {"AVIATIONSTACK_API_KEY": "SECRET_KEY"}, clear=True):
            service = AviationstackService()

        service.session = Mock()
        service.session.get.return_value = FakeResponse(status_code=403, http_error=True)

        with self.assertRaises(RuntimeError) as context:
            service.get_flights()

        self.assertIn("access was denied", str(context.exception).lower())

    def test_get_flights_maps_http_429_to_quota_error(self):
        with patch.dict(os.environ, {"AVIATIONSTACK_API_KEY": "SECRET_KEY"}, clear=True):
            service = AviationstackService()

        service.session = Mock()
        service.session.get.return_value = FakeResponse(status_code=429, http_error=True)

        with self.assertRaises(RuntimeError) as context:
            service.get_flights()

        self.assertIn("limit", str(context.exception).lower())

    def test_get_flights_maps_network_error_safely(self):
        with patch.dict(os.environ, {"AVIATIONSTACK_API_KEY": "SECRET_KEY"}, clear=True):
            service = AviationstackService()

        service.session = Mock()
        service.session.get.side_effect = requests.RequestException(
            "Network failed with access_key=SECRET_KEY"
        )

        with self.assertRaises(RuntimeError) as context:
            service.get_flights()

        self.assertIn("network request failed", str(context.exception).lower())
        self.assertNotIn("SECRET_KEY", str(context.exception))

    def test_get_flights_rejects_invalid_json(self):
        with patch.dict(os.environ, {"AVIATIONSTACK_API_KEY": "SECRET_KEY"}, clear=True):
            service = AviationstackService()

        service.session = Mock()
        service.session.get.return_value = FakeResponse(json_error="invalid json")

        with self.assertRaises(RuntimeError) as context:
            service.get_flights()

        self.assertIn("invalid json", str(context.exception).lower())

    def test_get_flights_maps_provider_error_codes(self):
        provider_errors = [
            ("invalid_access_key", "authentication error"),
            ("https_access_restricted", "access restriction"),
            ("usage_limit_reached", "quota error"),
            ("unknown_provider_error", "api error"),
        ]

        for code, expected_message in provider_errors:
            with self.subTest(code=code):
                with patch.dict(os.environ, {"AVIATIONSTACK_API_KEY": "SECRET_KEY"}, clear=True):
                    service = AviationstackService()

                service.session = Mock()
                service.session.get.return_value = FakeResponse(
                    payload={
                        "error": {
                            "code": code,
                            "message": "Provider error with access_key=SECRET_KEY",
                        }
                    }
                )

                with self.assertRaises(RuntimeError) as context:
                    service.get_flights()

                self.assertIn(expected_message, str(context.exception).lower())
                self.assertNotIn("SECRET_KEY", str(context.exception))

    def test_get_flights_requires_data_field(self):
        with patch.dict(os.environ, {"AVIATIONSTACK_API_KEY": "SECRET_KEY"}, clear=True):
            service = AviationstackService()

        service.session = Mock()
        service.session.get.return_value = FakeResponse(payload={"pagination": {}})

        with self.assertRaises(RuntimeError) as context:
            service.get_flights()

        self.assertIn("data", str(context.exception).lower())


class FlightSyncServiceHelperTests(TestCase):
    def make_service(self):
        with patch.dict(os.environ, {"AVIATIONSTACK_API_KEY": "SECRET_KEY"}, clear=True):
            return FlightSyncService()

    def test_cleaning_helpers_normalize_text_and_codes(self):
        service = self.make_service()

        self.assertIsNone(service._clean_text(None))
        self.assertIsNone(service._clean_text("   "))
        self.assertEqual(service._clean_text("  Alpha Airways  "), "Alpha Airways")

        self.assertIsNone(service._clean_code(None))
        self.assertEqual(service._clean_code(" msq "), "MSQ")

    def test_parse_datetime_accepts_zulu_naive_and_invalid_values(self):
        service = self.make_service()

        zulu = service._parse_datetime("2026-05-14T10:30:00Z")
        naive = service._parse_datetime("2026-05-14T10:30:00")
        invalid = service._parse_datetime("not-a-date")

        self.assertIsNotNone(zulu)
        self.assertIsNotNone(zulu.tzinfo)

        self.assertIsNotNone(naive)
        self.assertIsNotNone(naive.tzinfo)

        self.assertIsNone(invalid)

    def test_parse_decimal_and_coordinates_are_safe(self):
        service = self.make_service()

        self.assertEqual(service._parse_decimal("53.8825"), Decimal("53.8825"))
        self.assertEqual(service._parse_decimal("wrong", default=Decimal("0")), Decimal("0"))
        self.assertEqual(service._parse_coordinate("28.0307"), Decimal("28.0307"))
        self.assertTrue(service._has_meaningful_coordinate(Decimal("0")))
        self.assertFalse(service._has_meaningful_coordinate(None))

    def test_status_mapping_falls_back_to_scheduled(self):
        service = self.make_service()

        self.assertEqual(service._map_status("scheduled"), "scheduled")
        self.assertEqual(service._map_status("active"), "in_air")
        self.assertEqual(service._map_status("landed"), "landed")
        self.assertEqual(service._map_status("cancelled"), "cancelled")
        self.assertEqual(service._map_status("incident"), "delayed")
        self.assertEqual(service._map_status("diverted"), "delayed")
        self.assertEqual(service._map_status("unknown"), "scheduled")
        self.assertEqual(service._map_status(None), "scheduled")

    def test_build_snapshot_returns_current_flight_state(self):
        service = self.make_service()

        airline = Airline.objects.create(
            name="Snapshot Airways",
            iata_code="SA",
            icao_code="SNA",
            country="Belarus",
        )
        origin = Airport.objects.create(
            name="Minsk",
            iata_code="MSQ",
            icao_code="UMMS",
            latitude=53.882500,
            longitude=28.030700,
        )
        destination = Airport.objects.create(
            name="Paris",
            iata_code="CDG",
            icao_code="LFPG",
            latitude=49.009700,
            longitude=2.547900,
        )

        now = timezone.now()

        flight = Flight.objects.create(
            flight_number="SN100",
            airline=airline,
            origin_airport=origin,
            destination_airport=destination,
            scheduled_departure=now,
            scheduled_arrival=now + timezone.timedelta(hours=3),
            status="scheduled",
            source_type="api",
            external_id="EXT-SN100",
            live_latitude=50.0,
            live_longitude=20.0,
        )

        snapshot = service._build_snapshot(flight)

        self.assertEqual(snapshot["status"], "scheduled")
        self.assertEqual(snapshot["source_type"], "api")
        self.assertEqual(snapshot["external_id"], "EXT-SN100")
        self.assertEqual(snapshot["live_latitude"], 50.0)
        self.assertIsNone(service._build_snapshot(None))

    def test_will_generate_history_detects_created_and_changed_values(self):
        service = self.make_service()

        previous = {
            "status": "scheduled",
            "source_type": "api",
            "scheduled_departure": "A",
            "scheduled_arrival": "B",
            "actual_departure": None,
            "actual_arrival": None,
            "live_latitude": None,
            "live_longitude": None,
            "live_altitude": None,
            "live_speed": None,
            "live_direction": None,
            "external_id": "OLD",
        }

        same_values = dict(previous)
        changed_values = dict(previous)
        changed_values["status"] = "in_air"

        self.assertTrue(
            service._will_generate_history(
                previous_snapshot=None,
                current_values=same_values,
                created=False,
            )
        )
        self.assertTrue(
            service._will_generate_history(
                previous_snapshot=previous,
                current_values=same_values,
                created=True,
            )
        )
        self.assertFalse(
            service._will_generate_history(
                previous_snapshot=previous,
                current_values=same_values,
                created=False,
            )
        )
        self.assertTrue(
            service._will_generate_history(
                previous_snapshot=previous,
                current_values=changed_values,
                created=False,
            )
        )


class FlightSyncServiceDatabaseTests(TestCase):
    def make_service(self):
        with patch.dict(os.environ, {"AVIATIONSTACK_API_KEY": "SECRET_KEY"}, clear=True):
            return FlightSyncService()

    def make_payload_item(
        self,
        *,
        flight_iata="AA100",
        airline_name="Alpha Airways",
        airline_iata="AA",
        airline_icao="AAA",
        dep_airport="Minsk National Airport",
        dep_iata="MSQ",
        dep_icao="UMMS",
        arr_airport="Paris Charles de Gaulle",
        arr_iata="CDG",
        arr_icao="LFPG",
        flight_status="active",
        scheduled_departure="2026-05-14T10:00:00Z",
        scheduled_arrival="2026-05-14T13:00:00Z",
        live=True,
    ):
        item = {
            "flight_date": "2026-05-14",
            "flight_status": flight_status,
            "airline": {
                "name": airline_name,
                "iata": airline_iata,
                "icao": airline_icao,
            },
            "departure": {
                "airport": dep_airport,
                "iata": dep_iata,
                "icao": dep_icao,
                "city": "Minsk",
                "country": "Belarus",
                "latitude": "53.8825",
                "longitude": "28.0307",
                "scheduled": scheduled_departure,
                "actual": None,
            },
            "arrival": {
                "airport": arr_airport,
                "iata": arr_iata,
                "icao": arr_icao,
                "city": "Paris",
                "country": "France",
                "latitude": "49.0097",
                "longitude": "2.5479",
                "scheduled": scheduled_arrival,
                "actual": None,
            },
            "flight": {
                "iata": flight_iata,
                "icao": f"{flight_iata}X",
                "number": flight_iata.replace("AA", ""),
            },
            "live": {},
        }

        if live:
            item["live"] = {
                "updated": "2026-05-14T11:00:00Z",
                "latitude": 51.0,
                "longitude": 12.0,
                "altitude": 11000,
                "speed_horizontal": 760,
                "direction": 90,
            }

        return item

    def test_get_or_create_airline_creates_and_updates_airline(self):
        service = self.make_service()

        airline = service._get_or_create_airline(
            airline_name="Alpha Airways",
            airline_iata="AA",
            airline_icao="AAA",
        )

        self.assertIsNotNone(airline)
        self.assertEqual(airline.name, "Alpha Airways")
        self.assertEqual(airline.iata_code, "AA")

        updated_airline = service._get_or_create_airline(
            airline_name="Alpha Airways Updated",
            airline_iata="AA",
            airline_icao="AAA",
        )

        self.assertEqual(updated_airline.id, airline.id)
        self.assertEqual(updated_airline.name, "Alpha Airways Updated")

        incomplete = service._get_or_create_airline(
            airline_name="Incomplete Airways",
            airline_iata=None,
            airline_icao=None,
        )

        self.assertIsNone(incomplete)

    def test_get_or_create_airport_creates_and_updates_airport(self):
        service = self.make_service()

        airport = service._get_or_create_airport(
            airport_name="Minsk National Airport",
            iata_code="MSQ",
            icao_code="UMMS",
            city="Minsk",
            country="Belarus",
            latitude="53.8825",
            longitude="28.0307",
        )

        self.assertIsNotNone(airport)
        self.assertEqual(airport.iata_code, "MSQ")
        self.assertEqual(airport.latitude, Decimal("53.8825"))

        updated_airport = service._get_or_create_airport(
            airport_name="Minsk Airport Updated",
            iata_code="MSQ",
            icao_code="UMMS",
            city="Minsk",
            country="Belarus",
            latitude="53.9000",
            longitude="28.1000",
        )

        self.assertEqual(updated_airport.id, airport.id)
        self.assertEqual(updated_airport.name, "Minsk Airport Updated")
        self.assertEqual(updated_airport.latitude, Decimal("53.9000"))

        incomplete = service._get_or_create_airport(
            airport_name="Incomplete Airport",
            iata_code=None,
            icao_code=None,
        )

        self.assertIsNone(incomplete)

    def test_sync_flights_creates_api_flight_and_success_log(self):
        service = self.make_service()
        service.client = Mock()
        service.client.api_key = "SECRET_KEY"
        service.client.get_flights.return_value = {
            "data": [
                self.make_payload_item(
                    flight_iata="AA100",
                    flight_status="active",
                )
            ]
        }

        result = service.sync_flights(
            flight_iata="AA100",
            dep_iata="MSQ",
            arr_iata="CDG",
            limit=1,
        )

        self.assertEqual(result["received"], 1)
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["skipped_local"], 0)
        self.assertEqual(result["skipped_incomplete"], 0)
        self.assertEqual(result["history_created"], 1)

        flight = Flight.objects.get(flight_number="AA100")

        self.assertEqual(flight.status, "in_air")
        self.assertEqual(flight.source_type, "api")
        self.assertEqual(flight.airline.iata_code, "AA")
        self.assertEqual(flight.origin_airport.iata_code, "MSQ")
        self.assertEqual(flight.destination_airport.iata_code, "CDG")
        self.assertEqual(flight.live_latitude, 51.0)
        self.assertEqual(flight.live_speed, 760)

        log = ApiSyncLog.objects.latest("started_at")

        self.assertEqual(log.status, "success")
        self.assertEqual(log.records_received, 1)
        self.assertEqual(log.records_created, 1)
        self.assertEqual(log.records_updated, 0)
        self.assertIn("Sync completed successfully", log.message)

        service.client.get_flights.assert_called_once_with(
            flight_iata="AA100",
            dep_iata="MSQ",
            arr_iata="CDG",
            limit=1,
        )

    def test_sync_flights_updates_existing_api_flight(self):
        service = self.make_service()

        airline = Airline.objects.create(
            name="Alpha Airways",
            iata_code="AA",
            icao_code="AAA",
            country="Belarus",
        )
        origin = Airport.objects.create(
            name="Minsk National Airport",
            iata_code="MSQ",
            icao_code="UMMS",
            latitude=53.882500,
            longitude=28.030700,
        )
        destination = Airport.objects.create(
            name="Paris Charles de Gaulle",
            iata_code="CDG",
            icao_code="LFPG",
            latitude=49.009700,
            longitude=2.547900,
        )

        old_departure = timezone.now() + timezone.timedelta(hours=1)
        old_arrival = old_departure + timezone.timedelta(hours=3)

        Flight.objects.create(
            flight_number="AA200",
            airline=airline,
            origin_airport=origin,
            destination_airport=destination,
            scheduled_departure=old_departure,
            scheduled_arrival=old_arrival,
            status="scheduled",
            source_type="api",
            external_id="OLD",
        )

        service.client = Mock()
        service.client.api_key = "SECRET_KEY"
        service.client.get_flights.return_value = {
            "data": [
                self.make_payload_item(
                    flight_iata="AA200",
                    flight_status="landed",
                    scheduled_departure="2026-05-14T10:00:00Z",
                    scheduled_arrival="2026-05-14T13:00:00Z",
                )
            ]
        }

        result = service.sync_flights(limit=1)

        self.assertEqual(result["received"], 1)
        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["history_created"], 1)

        flight = Flight.objects.get(flight_number="AA200")
        self.assertEqual(flight.status, "landed")
        self.assertEqual(flight.source_type, "api")

        log = ApiSyncLog.objects.latest("started_at")
        self.assertEqual(log.status, "success")
        self.assertEqual(log.records_updated, 1)

    def test_sync_flights_skips_existing_local_flight(self):
        service = self.make_service()

        airline = Airline.objects.create(
            name="Local Airways",
            iata_code="LA",
            icao_code="LAA",
            country="Belarus",
        )
        origin = Airport.objects.create(
            name="Local Origin",
            iata_code="LOR",
            icao_code="ULOR",
            latitude=53.0,
            longitude=28.0,
        )
        destination = Airport.objects.create(
            name="Local Destination",
            iata_code="LDE",
            icao_code="ULDE",
            latitude=50.0,
            longitude=25.0,
        )

        now = timezone.now()

        Flight.objects.create(
            flight_number="AA300",
            airline=airline,
            origin_airport=origin,
            destination_airport=destination,
            scheduled_departure=now,
            scheduled_arrival=now + timezone.timedelta(hours=2),
            status="scheduled",
            source_type="local",
        )

        service.client = Mock()
        service.client.api_key = "SECRET_KEY"
        service.client.get_flights.return_value = {
            "data": [
                self.make_payload_item(
                    flight_iata="AA300",
                    flight_status="active",
                )
            ]
        }

        result = service.sync_flights(limit=1)

        self.assertEqual(result["received"], 1)
        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["skipped_local"], 1)

        flight = Flight.objects.get(flight_number="AA300")
        self.assertEqual(flight.source_type, "local")
        self.assertEqual(flight.status, "scheduled")

    def test_sync_flights_skips_incomplete_records(self):
        service = self.make_service()

        incomplete_item = self.make_payload_item(
            flight_iata="AA400",
            airline_name=None,
        )

        service.client = Mock()
        service.client.api_key = "SECRET_KEY"
        service.client.get_flights.return_value = {
            "data": [
                incomplete_item,
                self.make_payload_item(
                    flight_iata="AA401",
                    dep_iata=None,
                    dep_icao=None,
                ),
            ]
        }

        result = service.sync_flights(limit=2)

        self.assertEqual(result["received"], 2)
        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["skipped_incomplete"], 2)

        self.assertFalse(Flight.objects.filter(flight_number="AA400").exists())
        self.assertFalse(Flight.objects.filter(flight_number="AA401").exists())

        log = ApiSyncLog.objects.latest("started_at")
        self.assertEqual(log.status, "success")
        self.assertEqual(log.records_received, 2)
        self.assertEqual(log.records_created, 0)

    def test_sync_flights_logs_failure_and_redacts_api_key(self):
        service = self.make_service()
        service.client = Mock()
        service.client.api_key = "SECRET_KEY"
        service.client.get_flights.side_effect = RuntimeError(
            "Provider failed with SECRET_KEY inside message"
        )

        with self.assertRaises(RuntimeError):
            service.sync_flights(limit=1)

        log = ApiSyncLog.objects.latest("started_at")

        self.assertEqual(log.status, "failed")
        self.assertNotIn("SECRET_KEY", log.message)
        self.assertIn("***REDACTED_API_KEY***", log.message)
        self.assertIsNotNone(log.finished_at)


class WeatherHazardServiceTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_clean_airports_removes_duplicates_invalid_and_missing_coordinates(self):
        airports = [
            {"code": "msq", "city": "Minsk", "lat": "53.8825", "lng": "28.0307"},
            {"code": "MSQ", "city": "Duplicate", "lat": "53.8825", "lng": "28.0307"},
            {"code": "", "city": "No code", "lat": "10", "lng": "10"},
            {"code": "BAD", "city": "Bad latitude", "lat": "150", "lng": "10"},
            {"code": "NOC", "city": "No coordinates", "lat": None, "lng": "10"},
            {"code": "CDG", "city": "Paris", "lat": "49.0097", "lng": "2.5479"},
        ]

        clean = WeatherHazardService._clean_airports(airports)

        self.assertEqual(len(clean), 2)
        self.assertEqual(clean[0].code, "MSQ")
        self.assertEqual(clean[0].city, "Minsk")
        self.assertEqual(clean[0].lat, 53.8825)
        self.assertEqual(clean[1].code, "CDG")

    def test_weather_code_helpers_detect_storm_rain_and_snow(self):
        self.assertTrue(WeatherHazardService._is_storm_weather_code(95))
        self.assertFalse(WeatherHazardService._is_storm_weather_code(61))

        self.assertTrue(WeatherHazardService._is_rain_weather_code(61))
        self.assertFalse(WeatherHazardService._is_rain_weather_code(0))

        self.assertTrue(WeatherHazardService._is_snow_weather_code(71))
        self.assertFalse(WeatherHazardService._is_snow_weather_code(3))

    def test_numeric_helpers_are_safe(self):
        self.assertEqual(WeatherHazardService._to_float("10.5"), 10.5)
        self.assertEqual(WeatherHazardService._to_float(None, None), None)
        self.assertEqual(WeatherHazardService._to_float("nan", 0.0), 0.0)
        self.assertEqual(WeatherHazardService._to_float("wrong", 7.0), 7.0)

        self.assertEqual(WeatherHazardService._to_int("95"), 95)
        self.assertIsNone(WeatherHazardService._to_int(None))
        self.assertIsNone(WeatherHazardService._to_int("wrong"))

        self.assertEqual(WeatherHazardService._format_unix_utc(0), "00:00 UTC")
        self.assertIsNone(WeatherHazardService._format_unix_utc("wrong"))

    def test_classify_airport_weather_detects_high_storm_risk(self):
        airport = AirportWeatherPoint(
            code="MSQ",
            city="Minsk",
            lat=53.8825,
            lng=28.0307,
        )

        record = WeatherHazardService._classify_airport_weather(
            airport,
            {
                "time": "2026-05-14T10:00",
                "precipitation": 8.5,
                "rain": 1.0,
                "showers": 0.0,
                "snowfall": 0.0,
                "weather_code": 95,
                "wind_speed_10m": 30,
                "wind_gusts_10m": 65,
                "visibility": 5000,
            },
        )

        self.assertEqual(record["airport"], "MSQ")
        self.assertTrue(record["rain"])
        self.assertTrue(record["storm"])
        self.assertTrue(record["turbulence"])
        self.assertTrue(record["low_visibility"])
        self.assertEqual(record["severity"], "high")
        self.assertEqual(record["source"], "Open-Meteo")

    def test_classify_airport_weather_detects_medium_rain_or_turbulence(self):
        airport = AirportWeatherPoint(
            code="CDG",
            city="Paris",
            lat=49.0097,
            lng=2.5479,
        )

        record = WeatherHazardService._classify_airport_weather(
            airport,
            {
                "time": "2026-05-14T11:00",
                "precipitation": 0.4,
                "rain": 0.1,
                "showers": 0.0,
                "snowfall": 0.0,
                "weather_code": 61,
                "wind_speed_10m": 36,
                "wind_gusts_10m": 46,
                "visibility": 10000,
            },
        )

        self.assertTrue(record["rain"])
        self.assertFalse(record["storm"])
        self.assertTrue(record["turbulence"])
        self.assertFalse(record["low_visibility"])
        self.assertEqual(record["severity"], "medium")

    def test_classify_airport_weather_keeps_low_when_conditions_are_clear(self):
        airport = AirportWeatherPoint(
            code="BER",
            city="Berlin",
            lat=52.3667,
            lng=13.5033,
        )

        record = WeatherHazardService._classify_airport_weather(
            airport,
            {
                "time": "2026-05-14T12:00",
                "precipitation": 0,
                "rain": 0,
                "showers": 0,
                "snowfall": 0,
                "weather_code": 0,
                "wind_speed_10m": 12,
                "wind_gusts_10m": 18,
                "visibility": 10000,
            },
        )

        self.assertFalse(record["rain"])
        self.assertFalse(record["storm"])
        self.assertFalse(record["snow"])
        self.assertFalse(record["turbulence"])
        self.assertFalse(record["low_visibility"])
        self.assertEqual(record["severity"], "low")

    def test_build_summary_counts_weather_and_operational_signals(self):
        summary = WeatherHazardService._build_summary(
            weather_records=[
                {
                    "rain": True,
                    "storm": True,
                    "turbulence": True,
                    "snow": False,
                    "low_visibility": True,
                },
                {
                    "rain": False,
                    "storm": False,
                    "turbulence": True,
                    "snow": True,
                    "low_visibility": False,
                },
            ],
            operational_summary={
                "delayed": "2",
                "cancelled": "1",
                "high_risk": "3",
                "visible_flights": "15",
            },
        )

        self.assertEqual(summary["rain_records"], 1)
        self.assertEqual(summary["storm_records"], 1)
        self.assertEqual(summary["turbulence_records"], 2)
        self.assertEqual(summary["visibility_records"], 2)
        self.assertEqual(summary["delayed"], 2)
        self.assertEqual(summary["cancelled"], 1)
        self.assertEqual(summary["high_risk"], 3)
        self.assertEqual(summary["visible_flights"], 15)

    def test_get_latest_rainviewer_radar_returns_active_tile_url(self):
        payload = {
            "host": "https://tilecache.rainviewer.com",
            "radar": {
                "past": [
                    {
                        "time": 0,
                        "path": "/v2/radar/old",
                    }
                ],
                "nowcast": [
                    {
                        "time": 3600,
                        "path": "/v2/radar/latest",
                    }
                ],
            },
        }

        with patch("apps.integrations.services.weather_service.requests.get") as mocked_get:
            mocked_get.return_value = FakeResponse(payload=payload)

            radar = WeatherHazardService.get_latest_rainviewer_radar()

        self.assertTrue(radar["available"])
        self.assertEqual(radar["status"], "active")
        self.assertEqual(radar["provider"], "RainViewer")
        self.assertIn("/v2/radar/latest", radar["tile_url"])
        self.assertIn("{z}", radar["tile_url"])

        cached = cache.get(WeatherHazardService.RAINVIEWER_CACHE_KEY)
        self.assertEqual(cached, radar)

    def test_get_latest_rainviewer_radar_returns_standby_when_payload_is_incomplete(self):
        payload = {
            "host": "https://tilecache.rainviewer.com",
            "radar": {
                "past": [],
                "nowcast": [],
            },
        }

        with patch("apps.integrations.services.weather_service.requests.get") as mocked_get:
            mocked_get.return_value = FakeResponse(payload=payload)

            radar = WeatherHazardService.get_latest_rainviewer_radar()

        self.assertFalse(radar["available"])
        self.assertEqual(radar["status"], "standby")
        self.assertIsNone(radar["tile_url"])

    def test_get_latest_rainviewer_radar_handles_network_error(self):
        with patch("apps.integrations.services.weather_service.requests.get") as mocked_get:
            mocked_get.side_effect = requests.RequestException("network down")

            radar = WeatherHazardService.get_latest_rainviewer_radar()

        self.assertFalse(radar["available"])
        self.assertEqual(radar["status"], "standby")
        self.assertIn("failed", radar["message"].lower())

    def test_get_latest_rainviewer_radar_handles_invalid_json(self):
        with patch("apps.integrations.services.weather_service.requests.get") as mocked_get:
            mocked_get.return_value = FakeResponse(json_error="bad json")

            radar = WeatherHazardService.get_latest_rainviewer_radar()

        self.assertFalse(radar["available"])
        self.assertEqual(radar["status"], "standby")
        self.assertIn("invalid json", radar["message"].lower())

    def test_get_airport_weather_returns_classified_record_and_caches_it(self):
        airport = AirportWeatherPoint(
            code="MSQ",
            city="Minsk",
            lat=53.8825,
            lng=28.0307,
        )

        payload = {
            "current": {
                "time": "2026-05-14T10:00",
                "precipitation": 0.5,
                "rain": 0.2,
                "showers": 0,
                "snowfall": 0,
                "weather_code": 61,
                "wind_speed_10m": 20,
                "wind_gusts_10m": 30,
                "visibility": 9000,
            }
        }

        with patch("apps.integrations.services.weather_service.requests.get") as mocked_get:
            mocked_get.return_value = FakeResponse(payload=payload)

            record = WeatherHazardService.get_airport_weather(airport)
            cached_record = WeatherHazardService.get_airport_weather(airport)

        self.assertEqual(record["airport"], "MSQ")
        self.assertTrue(record["rain"])
        self.assertEqual(cached_record, record)
        mocked_get.assert_called_once()

    def test_get_airport_weather_returns_none_when_provider_fails(self):
        airport = AirportWeatherPoint(
            code="CDG",
            city="Paris",
            lat=49.0097,
            lng=2.5479,
        )

        with patch("apps.integrations.services.weather_service.requests.get") as mocked_get:
            mocked_get.side_effect = Exception("provider unavailable")

            record = WeatherHazardService.get_airport_weather(airport)

        self.assertIsNone(record)

    def test_get_airport_weather_records_limits_to_eight_airports(self):
        airports = [
            AirportWeatherPoint(
                code=f"A{i}",
                city="City",
                lat=10 + i,
                lng=20 + i,
            )
            for i in range(10)
        ]

        with patch.object(
            WeatherHazardService,
            "get_airport_weather",
            side_effect=lambda airport: {"airport": airport.code},
        ) as mocked_weather:
            records = WeatherHazardService.get_airport_weather_records(airports)

        self.assertEqual(len(records), 8)
        self.assertEqual(mocked_weather.call_count, 8)

    def test_build_weather_payload_combines_radar_weather_and_summary(self):
        airports = [
            {
                "code": "MSQ",
                "city": "Minsk",
                "lat": 53.8825,
                "lng": 28.0307,
            },
            {
                "code": "CDG",
                "city": "Paris",
                "lat": 49.0097,
                "lng": 2.5479,
            },
        ]

        with patch.object(
            WeatherHazardService,
            "get_latest_rainviewer_radar",
            return_value={
                "available": True,
                "status": "active",
                "tile_url": "https://example.test/{z}/{x}/{y}.png",
            },
        ):
            with patch.object(
                WeatherHazardService,
                "get_airport_weather_records",
                return_value=[
                    {
                        "airport": "MSQ",
                        "rain": True,
                        "storm": False,
                        "turbulence": True,
                        "snow": False,
                        "low_visibility": False,
                    },
                    {
                        "airport": "CDG",
                        "rain": False,
                        "storm": True,
                        "turbulence": False,
                        "snow": False,
                        "low_visibility": True,
                    },
                ],
            ):
                payload = WeatherHazardService.build_weather_payload(
                    airports=airports,
                    operational_summary={
                        "delayed": 2,
                        "cancelled": 1,
                        "high_risk": 3,
                        "visible_flights": 20,
                    },
                )

        self.assertTrue(payload["ok"])
        self.assertIn("RainViewer", payload["source"])
        self.assertIn("generated_at", payload)
        self.assertEqual(payload["radar"]["status"], "active")
        self.assertEqual(len(payload["hazards"]), 2)
        self.assertEqual(payload["summary"]["rain_records"], 1)
        self.assertEqual(payload["summary"]["storm_records"], 1)
        self.assertEqual(payload["summary"]["turbulence_records"], 1)
        self.assertEqual(payload["summary"]["visibility_records"], 1)
        self.assertEqual(payload["summary"]["visible_flights"], 20)


class IntegrationViewsBusinessTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(
            username="sync-view-tester",
            password="test-password",
        )

    def _attach_request_runtime(self, request):
        request.user = self.user

        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()

        request._messages = FallbackStorage(request)

        return request

    def test_user_safe_error_message_maps_provider_errors(self):
        cases = [
            (
                "invalid_access_key authentication failed",
                "provider authentication error",
            ),
            (
                "access was denied function_access_restricted",
                "provider access denied",
            ),
            (
                "usage_limit_reached rate_limit_reached",
                "usage or rate limit",
            ),
            (
                "network request failed",
                "network communication",
            ),
            (
                "invalid json",
                "invalid response format",
            ),
            (
                "unexpected provider problem",
                "provider request could not be completed",
            ),
        ]

        for raw_error, expected_fragment in cases:
            with self.subTest(raw_error=raw_error):
                message = views._build_user_safe_error_message(raw_error)
                self.assertIn(expected_fragment.lower(), message.lower())

    def test_get_log_duration_seconds_returns_duration_when_log_is_finished(self):
        started_at = timezone.now()
        finished_at = started_at + timezone.timedelta(seconds=12.6)

        log = ApiSyncLog.objects.create(
            provider_name="aviationstack",
            sync_type="flights",
            started_at=started_at,
            finished_at=finished_at,
            status="success",
            records_received=5,
            records_created=2,
            records_updated=3,
            message="Completed",
        )

        self.assertEqual(views._get_log_duration_seconds(log), 12.6)
        self.assertIsNone(views._get_log_duration_seconds(None))

        log.finished_at = None
        self.assertIsNone(views._get_log_duration_seconds(log))

    def test_clean_sync_limit_normalizes_invalid_low_and_high_values(self):
        self.assertEqual(views._clean_sync_limit(None), 10)
        self.assertEqual(views._clean_sync_limit("abc"), 10)
        self.assertEqual(views._clean_sync_limit("-5"), 1)
        self.assertEqual(views._clean_sync_limit("0"), 1)
        self.assertEqual(views._clean_sync_limit("25"), 25)
        self.assertEqual(views._clean_sync_limit("999"), 100)

    def test_safe_rate_handles_zero_and_regular_values(self):
        self.assertEqual(views._safe_rate(0, 0), 0)
        self.assertEqual(views._safe_rate(2, 4), 50.0)
        self.assertEqual(views._safe_rate(1, 3), 33.3)

    def test_build_provider_health_without_logs(self):
        health = views._build_provider_health(
            latest_log=None,
            failure_rate=0,
        )

        self.assertEqual(health["provider_health"], "No runs yet")
        self.assertEqual(health["provider_health_class"], "neutral")
        self.assertIn("No synchronization", health["provider_health_reason"])

    def test_build_provider_health_for_failed_latest_log(self):
        log = ApiSyncLog.objects.create(
            provider_name="aviationstack",
            sync_type="flights",
            started_at=timezone.now(),
            finished_at=timezone.now(),
            status="failed",
            records_received=0,
            records_created=0,
            records_updated=0,
            message="Provider failed",
        )

        health = views._build_provider_health(
            latest_log=log,
            failure_rate=20,
        )

        self.assertEqual(health["provider_health"], "Needs review")
        self.assertEqual(health["provider_health_class"], "critical")

    def test_build_provider_health_for_success_without_records(self):
        log = ApiSyncLog.objects.create(
            provider_name="aviationstack",
            sync_type="flights",
            started_at=timezone.now(),
            finished_at=timezone.now(),
            status="success",
            records_received=0,
            records_created=0,
            records_updated=0,
            message="No records",
        )

        health = views._build_provider_health(
            latest_log=log,
            failure_rate=0,
        )

        self.assertEqual(health["provider_health"], "No data received")
        self.assertEqual(health["provider_health_class"], "warning")

    def test_build_provider_health_for_unstable_history(self):
        log = ApiSyncLog.objects.create(
            provider_name="aviationstack",
            sync_type="flights",
            started_at=timezone.now(),
            finished_at=timezone.now(),
            status="success",
            records_received=10,
            records_created=4,
            records_updated=6,
            message="Completed",
        )

        health = views._build_provider_health(
            latest_log=log,
            failure_rate=50,
        )

        self.assertEqual(health["provider_health"], "Unstable history")
        self.assertEqual(health["provider_health_class"], "warning")

    def test_build_provider_health_for_available_provider(self):
        log = ApiSyncLog.objects.create(
            provider_name="aviationstack",
            sync_type="flights",
            started_at=timezone.now(),
            finished_at=timezone.now(),
            status="success",
            records_received=12,
            records_created=5,
            records_updated=7,
            message="Completed",
        )

        health = views._build_provider_health(
            latest_log=log,
            failure_rate=10,
        )

        self.assertEqual(health["provider_health"], "Available")
        self.assertEqual(health["provider_health_class"], "stable")

    def test_build_timeline_highlights_with_history(self):
        log = ApiSyncLog.objects.create(
            provider_name="aviationstack",
            sync_type="flights",
            started_at=timezone.now(),
            finished_at=timezone.now(),
            status="success",
            records_received=10,
            records_created=4,
            records_updated=6,
            message="Completed",
        )

        highlights = views._build_timeline_highlights(
            latest_log=log,
            total_runs=3,
            success_rate=66.7,
            total_received=20,
            total_created=8,
            total_updated=12,
        )

        self.assertGreaterEqual(len(highlights), 1)
        self.assertLessEqual(len(highlights), 4)
        self.assertIn("Last run", highlights[0])

    def test_build_timeline_highlights_without_history(self):
        highlights = views._build_timeline_highlights(
            latest_log=None,
            total_runs=0,
            success_rate=0,
            total_received=0,
            total_created=0,
            total_updated=0,
        )

        self.assertEqual(len(highlights), 1)
        self.assertIn("No synchronization history", highlights[0])

    def test_sync_page_get_builds_sync_dashboard_context(self):
        now = timezone.now()

        ApiSyncLog.objects.create(
            provider_name="aviationstack",
            sync_type="flights",
            started_at=now - timezone.timedelta(minutes=10),
            finished_at=now - timezone.timedelta(minutes=9),
            status="success",
            records_received=10,
            records_created=4,
            records_updated=6,
            message="Completed",
        )

        ApiSyncLog.objects.create(
            provider_name="aviationstack",
            sync_type="flights",
            started_at=now - timezone.timedelta(minutes=5),
            finished_at=now - timezone.timedelta(minutes=4),
            status="failed",
            records_received=0,
            records_created=0,
            records_updated=0,
            message="Provider failed",
        )

        request = self._attach_request_runtime(
            self.factory.get("/sync/")
        )

        with patch("apps.integrations.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.sync_page(request)

        self.assertEqual(response.status_code, 200)

        template_name = mocked_render.call_args.args[1]
        context = mocked_render.call_args.args[2]

        self.assertEqual(template_name, "integrations/sync.html")
        self.assertEqual(context["total_runs"], 2)
        self.assertEqual(context["success_count"], 1)
        self.assertEqual(context["failed_count"], 1)
        self.assertEqual(context["success_rate"], 50.0)
        self.assertEqual(context["failure_rate"], 50.0)

        self.assertEqual(context["total_received"], 10)
        self.assertEqual(context["total_created"], 4)
        self.assertEqual(context["total_updated"], 6)

        self.assertEqual(context["latest_status"], "Failed")
        self.assertEqual(context["latest_provider"], "aviationstack")
        self.assertIsNotNone(context["average_duration_seconds"])
        self.assertGreaterEqual(len(context["timeline_highlights"]), 1)
        self.assertEqual(len(context["recent_failures"]), 1)
        self.assertEqual(len(context["recent_successes"]), 1)

    def test_sync_page_get_without_logs_uses_safe_empty_context(self):
        request = self._attach_request_runtime(
            self.factory.get("/sync/")
        )

        with patch("apps.integrations.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.sync_page(request)

        self.assertEqual(response.status_code, 200)

        context = mocked_render.call_args.args[2]

        self.assertIsNone(context["latest_log"])
        self.assertEqual(context["latest_status"], "Unknown")
        self.assertEqual(context["latest_received"], 0)
        self.assertEqual(context["latest_created"], 0)
        self.assertEqual(context["latest_updated"], 0)
        self.assertEqual(context["success_count"], 0)
        self.assertEqual(context["failed_count"], 0)
        self.assertEqual(context["total_runs"], 0)
        self.assertEqual(context["total_received"], 0)
        self.assertEqual(context["total_created"], 0)
        self.assertEqual(context["total_updated"], 0)
        self.assertEqual(context["success_rate"], 0)
        self.assertEqual(context["failure_rate"], 0)
        self.assertEqual(context["provider_health"], "No runs yet")

    def test_sync_page_post_runs_sync_service_and_redirects(self):
        request = self._attach_request_runtime(
            self.factory.post(
                "/sync/",
                {
                    "dep_iata": " msq ",
                    "arr_iata": " cdg ",
                    "flight_iata": " aa100 ",
                    "limit": "5",
                },
            )
        )

        with patch("apps.integrations.views.FlightSyncService") as mocked_service_class:
            mocked_service = mocked_service_class.return_value
            mocked_service.sync_flights.return_value = {
                "received": 3,
                "created": 1,
                "updated": 2,
                "history_created": 3,
                "skipped_local": 0,
                "skipped_incomplete": 0,
            }

            with patch("apps.integrations.views.redirect") as mocked_redirect:
                mocked_redirect.return_value = SimpleNamespace(status_code=302)

                response = views.sync_page(request)

        self.assertEqual(response.status_code, 302)

        mocked_service.sync_flights.assert_called_once_with(
            flight_iata="AA100",
            dep_iata="MSQ",
            arr_iata="CDG",
            limit=5,
        )

        mocked_redirect.assert_called_once_with("integrations:sync_page")

    def test_sync_page_post_handles_service_error_and_redirects(self):
        request = self._attach_request_runtime(
            self.factory.post(
                "/sync/",
                {
                    "dep_iata": "MSQ",
                    "arr_iata": "CDG",
                    "flight_iata": "",
                    "limit": "200",
                },
            )
        )

        with patch("apps.integrations.views.FlightSyncService") as mocked_service_class:
            mocked_service = mocked_service_class.return_value
            mocked_service.sync_flights.side_effect = RuntimeError(
                "invalid_access_key provider problem"
            )

            with patch("apps.integrations.views.redirect") as mocked_redirect:
                mocked_redirect.return_value = SimpleNamespace(status_code=302)

                response = views.sync_page(request)

        self.assertEqual(response.status_code, 302)

        mocked_service.sync_flights.assert_called_once_with(
            flight_iata=None,
            dep_iata="MSQ",
            arr_iata="CDG",
            limit=100,
        )

        mocked_redirect.assert_called_once_with("integrations:sync_page")