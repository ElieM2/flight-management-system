import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.aircraft.models import Aircraft
from apps.airlines.models import Airline
from apps.airports.models import Airport
from apps.copilot.constants import COPILOT_INTENTS
from apps.copilot.repositories.flight_queries import FlightQueries
from apps.copilot.repositories.sync_queries import SyncQueries
from apps.copilot.services.copilot_service import CopilotService
from apps.copilot.services.intent_detector import IntentDetector
from apps.copilot.services.language_service import CopilotLanguageService
from apps.copilot.services.response_builder import ResponseBuilder
from apps.copilot.services.system_snapshot_service import SystemSnapshotService
from apps.copilot.views import CopilotAskView
from apps.flights.models import Flight
from apps.integrations.models import ApiSyncLog


class CopilotTestDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.airline_alpha = Airline.objects.create(
            name="Alpha Airways",
            iata_code="AA",
            icao_code="AAA",
            country="Belarus",
        )
        cls.airline_beta = Airline.objects.create(
            name="Beta Wings",
            iata_code="BW",
            icao_code="BTW",
            country="France",
        )

        cls.minsk = Airport.objects.create(
            name="Minsk National Airport",
            iata_code="MSQ",
            icao_code="UMMS",
            city="Minsk",
            country="Belarus",
            latitude=53.882500,
            longitude=28.030700,
        )
        cls.paris = Airport.objects.create(
            name="Paris Charles de Gaulle",
            iata_code="CDG",
            icao_code="LFPG",
            city="Paris",
            country="France",
            latitude=49.009700,
            longitude=2.547900,
        )
        cls.berlin = Airport.objects.create(
            name="Berlin Brandenburg",
            iata_code="BER",
            icao_code="EDDB",
            city="Berlin",
            country="Germany",
            latitude=52.366700,
            longitude=13.503300,
        )

        cls.aircraft = Aircraft.objects.create(
            airline=cls.airline_alpha,
            model="Airbus A320",
            registration_number="EW-TEST",
            aircraft_type="A320",
            capacity=180,
            status="active",
        )

        now = timezone.now()

        cls.flight_delayed = Flight.objects.create(
            flight_number="AA101",
            airline=cls.airline_alpha,
            aircraft=cls.aircraft,
            origin_airport=cls.minsk,
            destination_airport=cls.paris,
            scheduled_departure=now.replace(hour=8, minute=0, second=0, microsecond=0),
            scheduled_arrival=now.replace(hour=11, minute=0, second=0, microsecond=0),
            actual_departure=now.replace(hour=9, minute=0, second=0, microsecond=0),
            status="delayed",
            source_type="api",
            live_latitude=52.0,
            live_longitude=20.0,
            last_synced_at=now,
        )

        cls.flight_cancelled = Flight.objects.create(
            flight_number="AA202",
            airline=cls.airline_alpha,
            aircraft=cls.aircraft,
            origin_airport=cls.minsk,
            destination_airport=cls.berlin,
            scheduled_departure=now.replace(hour=10, minute=0, second=0, microsecond=0),
            scheduled_arrival=now.replace(hour=12, minute=0, second=0, microsecond=0),
            status="cancelled",
            source_type="local",
        )

        cls.flight_in_air = Flight.objects.create(
            flight_number="BW303",
            airline=cls.airline_beta,
            aircraft=None,
            origin_airport=cls.paris,
            destination_airport=cls.minsk,
            scheduled_departure=now.replace(hour=13, minute=0, second=0, microsecond=0),
            scheduled_arrival=now.replace(hour=16, minute=0, second=0, microsecond=0),
            status="in_air",
            source_type="api",
            live_latitude=50.0,
            live_longitude=10.0,
        )

        cls.flight_landed = Flight.objects.create(
            flight_number="BW404",
            airline=cls.airline_beta,
            aircraft=None,
            origin_airport=cls.berlin,
            destination_airport=cls.paris,
            scheduled_departure=now.replace(hour=6, minute=0, second=0, microsecond=0),
            scheduled_arrival=now.replace(hour=8, minute=0, second=0, microsecond=0),
            status="landed",
            source_type="local",
        )

        ApiSyncLog.objects.create(
            provider_name="Aviationstack",
            sync_type="flight_import",
            started_at=now,
            finished_at=now + timezone.timedelta(seconds=8),
            status="success",
            records_received=20,
            records_created=10,
            records_updated=5,
            message="Sync completed",
        )

        ApiSyncLog.objects.create(
            provider_name="Aviationstack",
            sync_type="flight_import",
            started_at=now - timezone.timedelta(hours=2),
            finished_at=now - timezone.timedelta(hours=2) + timezone.timedelta(seconds=4),
            status="failed",
            records_received=0,
            records_created=0,
            records_updated=0,
            message="Provider failed",
        )


class FlightQueriesBusinessTests(CopilotTestDataMixin, TestCase):
    def test_operational_summary_counts_core_business_metrics(self):
        summary = FlightQueries().get_operational_summary()

        self.assertEqual(summary["total_flights"], 4)
        self.assertEqual(summary["delayed_count"], 1)
        self.assertEqual(summary["cancelled_count"], 1)
        self.assertEqual(summary["in_air_count"], 1)
        self.assertEqual(summary["active_count"], 2)
        self.assertEqual(summary["completed_count"], 2)
        self.assertEqual(summary["api_flights"], 2)
        self.assertEqual(summary["local_flights"], 2)
        self.assertEqual(summary["live_tracked_count"], 2)
        self.assertEqual(summary["critical_count"], 2)
        self.assertEqual(summary["delay_rate"], 25.0)
        self.assertEqual(summary["cancellation_rate"], 25.0)
        self.assertEqual(summary["api_rate"], 50.0)

    def test_priority_flights_puts_cancelled_before_delayed(self):
        records = FlightQueries().get_priority_flights(limit=10)

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["status"], "cancelled")
        self.assertEqual(records[1]["status"], "delayed")
        self.assertEqual(records[0]["flight_number"], "AA202")

    def test_source_breakdown_returns_api_and_local_distribution(self):
        breakdown = FlightQueries().get_source_breakdown()

        self.assertEqual(breakdown["total_flights"], 4)
        self.assertEqual(breakdown["api_flights"], 2)
        self.assertEqual(breakdown["local_flights"], 2)
        self.assertEqual(breakdown["api_rate"], 50.0)
        self.assertEqual(breakdown["local_rate"], 50.0)

    def test_top_airline_airport_and_route_are_aggregated_from_real_flights(self):
        queries = FlightQueries()

        top_airline = queries.get_top_airlines(limit=1)[0]
        top_airport = queries.get_top_airports(limit=1)[0]
        top_route = queries.get_top_routes(limit=1)[0]

        self.assertEqual(top_airline["airline_name"], "Alpha Airways")
        self.assertEqual(top_airline["flight_count"], 2)

        self.assertIn(top_airport["airport_code"], ["MSQ", "BER", "CDG"])
        self.assertGreaterEqual(top_airport["flight_count"], 1)

        self.assertIn("→", top_route["route"])
        self.assertGreaterEqual(top_route["flight_count"], 1)

    def test_flights_by_airline_name_uses_partial_case_insensitive_match(self):
        records = FlightQueries().get_flights_by_airline_name("alpha", limit=10)

        self.assertEqual(len(records), 2)
        self.assertTrue(all("Alpha Airways" in record["airline"] for record in records))


class SyncQueriesBusinessTests(CopilotTestDataMixin, TestCase):
    def test_sync_status_summary_calculates_rates_and_totals(self):
        summary = SyncQueries().get_sync_status_summary()

        self.assertEqual(summary["total_logs"], 2)
        self.assertEqual(summary["success_count"], 1)
        self.assertEqual(summary["failed_count"], 1)
        self.assertEqual(summary["success_rate"], 50.0)
        self.assertEqual(summary["failure_rate"], 50.0)
        self.assertEqual(summary["total_records_received"], 20)
        self.assertEqual(summary["total_records_created"], 10)
        self.assertEqual(summary["total_records_updated"], 5)
        self.assertIsNotNone(summary["latest_log"])
        self.assertIsNotNone(summary["last_successful_log"])

    def test_recent_logs_are_serialized_with_duration(self):
        records = SyncQueries().get_recent_logs(limit=2)

        self.assertEqual(len(records), 2)
        self.assertIn("provider_name", records[0])
        self.assertIn("duration_seconds", records[0])
        self.assertIsInstance(records[0]["duration_seconds"], int)


class SystemSnapshotServiceTests(CopilotTestDataMixin, TestCase):
    def test_snapshot_combines_flight_sync_source_and_attention_sections(self):
        snapshot = SystemSnapshotService().build_snapshot()

        self.assertIn("generated_at", snapshot)
        self.assertIn("flight_summary", snapshot)
        self.assertIn("source_breakdown", snapshot)
        self.assertIn("critical_attention", snapshot)
        self.assertIn("api_sync_status", snapshot)

        self.assertEqual(snapshot["flight_summary"]["total_flights"], 4)
        self.assertEqual(snapshot["critical_attention"]["critical_count"], 2)
        self.assertEqual(snapshot["api_sync_status"]["total_logs"], 2)


class IntentDetectorBusinessTests(TestCase):
    def setUp(self):
        self.detector = IntentDetector()

    def test_detects_multilingual_operational_summary(self):
        french = self.detector.detect("Donne moi le résumé opérationnel")
        russian = self.detector.detect("Покажи текущая операционная ситуация")

        self.assertEqual(french["intent"], COPILOT_INTENTS["OPERATIONAL_SUMMARY"])
        self.assertEqual(russian["intent"], COPILOT_INTENTS["OPERATIONAL_SUMMARY"])

    def test_detects_delayed_cancelled_priority_and_sync_intents(self):
        delayed = self.detector.detect("Show delayed flights")
        cancelled = self.detector.detect("Montre les vols annulés")
        priority = self.detector.detect("Which flights need attention?")
        sync = self.detector.detect("What is the API sync status?")

        self.assertEqual(delayed["intent"], COPILOT_INTENTS["DELAYED_FLIGHTS"])
        self.assertEqual(cancelled["intent"], COPILOT_INTENTS["CANCELLED_FLIGHTS"])
        self.assertEqual(priority["intent"], COPILOT_INTENTS["PRIORITY_FLIGHTS"])
        self.assertEqual(sync["intent"], COPILOT_INTENTS["API_SYNC_STATUS"])

    def test_detects_status_and_airline_queries(self):
        status_result = self.detector.detect("Show me in air flights")
        airline_result = self.detector.detect("Show flights for Alpha Airways")

        self.assertEqual(status_result["intent"], "FLIGHTS_BY_STATUS")
        self.assertEqual(status_result["extracted_value"], "in_air")

        self.assertEqual(airline_result["intent"], "FLIGHTS_BY_AIRLINE")
        self.assertEqual(airline_result["extracted_value"], "alpha airways")


class CopilotLanguageServiceTests(TestCase):
    def setUp(self):
        self.service = CopilotLanguageService()

    def test_detect_language_returns_english_for_empty_message(self):
        self.assertEqual(self.service.detect_language(""), "en")
        self.assertEqual(self.service.detect_language("   "), "en")
        self.assertEqual(self.service.detect_language(None), "en")

    def test_detect_language_detects_russian_from_cyrillic(self):
        self.assertEqual(
            self.service.detect_language("Покажи текущую операционную ситуацию"),
            "ru",
        )
        self.assertEqual(
            self.service.detect_language("Сколько задержанных рейсов?"),
            "ru",
        )

    def test_detect_language_detects_french_from_operational_markers(self):
        french_messages = [
            "Bonjour",
            "Salut",
            "Bonsoir",
            "Donne moi le résumé opérationnel",
            "Montre les vols retardés",
            "Combien de vols annulés ?",
            "Explique la synchronisation API",
            "Quelle compagnie est la plus active ?",
            "Structure de la base de données",
            "Quels vols sont en retard ?",
        ]

        for message in french_messages:
            with self.subTest(message=message):
                self.assertEqual(self.service.detect_language(message), "fr")

    def test_detect_language_falls_back_to_english(self):
        english_messages = [
            "Show me the current flight overview",
            "What is the API sync status?",
            "Show delayed flights",
            "Which route is the busiest?",
        ]

        for message in english_messages:
            with self.subTest(message=message):
                self.assertEqual(self.service.detect_language(message), "en")

    def test_contains_cyrillic_detects_russian_letters(self):
        self.assertTrue(self.service._contains_cyrillic("рейсы"))
        self.assertTrue(self.service._contains_cyrillic("операционная ситуация"))
        self.assertFalse(self.service._contains_cyrillic("flights"))
        self.assertFalse(self.service._contains_cyrillic("operational summary"))

    def test_text_returns_supported_language_template(self):
        self.assertEqual(
            self.service.text("empty_title", "en"),
            "Write an operational question",
        )
        self.assertEqual(
            self.service.text("empty_title", "fr"),
            "Écris une question opérationnelle",
        )
        self.assertEqual(
            self.service.text("empty_title", "ru"),
            "Введите операционный вопрос",
        )

    def test_text_falls_back_to_english_for_unknown_language(self):
        self.assertEqual(
            self.service.text("empty_title", "de"),
            "Write an operational question",
        )
        self.assertEqual(
            self.service.text("greeting_title", "es"),
            "Operational Copilot",
        )

    def test_text_returns_key_when_template_does_not_exist(self):
        self.assertEqual(
            self.service.text("missing_template_key", "en"),
            "missing_template_key",
        )

    def test_text_formats_template_with_kwargs(self):
        self.assertEqual(
            self.service.text("delayed_count", "en", delayed_count=3),
            "Delayed flights: 3.",
        )
        self.assertEqual(
            self.service.text("cancelled_count", "fr", cancelled_count=2),
            "Vols annulés : 2.",
        )
        self.assertEqual(
            self.service.text("live_tracked_count", "ru", live_tracked_count=5),
            "Рейсы с доступным отслеживанием: 5.",
        )

    def test_text_returns_template_when_formatting_fails(self):
        result = self.service.text("delayed_count", "en")

        self.assertEqual(result, "Delayed flights: {delayed_count}.")

    def test_text_returns_multilingual_operational_summary_messages(self):
        french = self.service.text(
            "operational_summary_message_attention",
            "fr",
            total_flights=10,
            active_count=6,
            critical_count=2,
        )

        russian = self.service.text(
            "operational_summary_message_stable",
            "ru",
            total_flights=8,
            active_count=5,
        )

        english = self.service.text(
            "operational_summary_message_stable",
            "en",
            total_flights=7,
            active_count=4,
        )

        self.assertIn("10 vols", french)
        self.assertIn("6 enregistrements", french)
        self.assertIn("8 рейсов", russian)
        self.assertIn("7 flights", english)

    def test_text_returns_multilingual_api_sync_messages(self):
        success_fr = self.service.text(
            "api_sync_success",
            "fr",
            latest_provider="Aviationstack",
            latest_status="success",
        )

        failed_en = self.service.text(
            "api_sync_failed",
            "en",
            latest_provider="Aviationstack",
            latest_sync_type="flight_import",
            latest_status="failed",
        )

        failed_ru = self.service.text(
            "api_sync_failed",
            "ru",
            latest_provider="Aviationstack",
            latest_sync_type="flight_import",
            latest_status="failed",
        )

        self.assertIn("Aviationstack", success_fr)
        self.assertIn("success", success_fr)
        self.assertIn("flight_import", failed_en)
        self.assertIn("failed", failed_en)
        self.assertIn("Aviationstack", failed_ru)

    def test_text_returns_database_and_unknown_messages(self):
        database_fr = self.service.text("database_message", "fr")
        unknown_ru = self.service.text("unknown_message", "ru")
        source_en = self.service.text("stored_data_note", "en")

        self.assertIn("données de référence", database_fr)
        self.assertIn("операционной задачей", unknown_ru)
        self.assertIn("stored system records", source_en)


class ResponseBuilderTests(TestCase):
    def test_response_builder_keeps_stable_frontend_payload_shape(self):
        payload = ResponseBuilder().build(
            response_type="DATA_BASED",
            intent="TEST_INTENT",
            title=" Test title ",
            message=" Test message ",
        )

        expected_keys = {
            "type",
            "intent",
            "title",
            "message",
            "bullets",
            "metrics",
            "records",
            "recommended_module",
            "recommended_url",
            "confidence",
            "source_note",
            "rewritten_message",
            "suggested_prompts",
        }

        self.assertEqual(set(payload.keys()), expected_keys)
        self.assertEqual(payload["title"], "Test title")
        self.assertEqual(payload["message"], "Test message")
        self.assertEqual(payload["bullets"], [])
        self.assertEqual(payload["metrics"], {})
        self.assertEqual(payload["records"], [])


class CopilotServiceBusinessLogicTests(CopilotTestDataMixin, TestCase):
    def setUp(self):
        self.rewrite_patch = patch(
            "apps.copilot.services.copilot_service.CopilotAnswerRewriter.rewrite",
            return_value=SimpleNamespace(
                ok=False,
                text="",
                error="rewriter disabled during tests",
            ),
        )
        self.rewrite_patch.start()
        self.addCleanup(self.rewrite_patch.stop)

        self.service = CopilotService()

    def test_empty_message_returns_unavailable_response(self):
        response = self.service.handle_message("   ", interface_language="en")

        self.assertEqual(response["type"], "unavailable")
        self.assertEqual(response["intent"], COPILOT_INTENTS["UNKNOWN"])
        self.assertEqual(response["rewrite_source"], "original")

    def test_operational_summary_uses_database_counts(self):
        response = self.service.handle_message(
            "Give me the current operational summary",
            interface_language="en",
        )

        self.assertEqual(response["intent"], COPILOT_INTENTS["OPERATIONAL_SUMMARY"])
        self.assertEqual(response["metrics"]["total_flights"], 4)
        self.assertEqual(response["metrics"]["delayed_count"], 1)
        self.assertEqual(response["metrics"]["cancelled_count"], 1)
        self.assertEqual(response["recommended_module"], "Monitoring Map")

    def test_delayed_flights_returns_delayed_records(self):
        response = self.service.handle_message("Show delayed flights", interface_language="en")

        self.assertEqual(response["intent"], COPILOT_INTENTS["DELAYED_FLIGHTS"])
        self.assertEqual(response["metrics"]["delayed_count"], 1)
        self.assertEqual(len(response["records"]), 1)
        self.assertEqual(response["records"][0]["flight_number"], "AA101")

    def test_cancelled_flights_returns_cancelled_records(self):
        response = self.service.handle_message("Show cancelled flights", interface_language="en")

        self.assertEqual(response["intent"], COPILOT_INTENTS["CANCELLED_FLIGHTS"])
        self.assertEqual(response["metrics"]["cancelled_count"], 1)
        self.assertEqual(response["records"][0]["flight_number"], "AA202")

    def test_priority_flights_separates_delayed_and_cancelled_counts(self):
        response = self.service.handle_message("Which flights need attention?", interface_language="en")

        self.assertEqual(response["intent"], COPILOT_INTENTS["PRIORITY_FLIGHTS"])
        self.assertEqual(response["metrics"]["critical_count"], 2)
        self.assertEqual(response["metrics"]["cancelled_count"], 1)
        self.assertEqual(response["metrics"]["delayed_count"], 1)

    def test_api_sync_status_uses_latest_log_and_history(self):
        response = self.service.handle_message("What is the API sync status?", interface_language="en")

        self.assertEqual(response["intent"], COPILOT_INTENTS["API_SYNC_STATUS"])
        self.assertEqual(response["metrics"]["total_logs"], 2)
        self.assertEqual(response["metrics"]["success_rate"], 50.0)
        self.assertEqual(len(response["records"]), 2)
        self.assertEqual(response["recommended_module"], "Data Sync")

    def test_source_breakdown_detects_balanced_dataset(self):
        response = self.service.handle_message("Show source breakdown", interface_language="en")

        self.assertEqual(response["intent"], COPILOT_INTENTS["SOURCE_BREAKDOWN"])
        self.assertEqual(response["metrics"]["api_flights"], 2)
        self.assertEqual(response["metrics"]["local_flights"], 2)
        self.assertIn("balanced", response["message"].lower())

    def test_top_airline_top_airport_and_top_route_are_supported(self):
        airline = self.service.handle_message("What is the top airline?", interface_language="en")
        airport = self.service.handle_message("What is the busiest airport?", interface_language="en")
        route = self.service.handle_message("What is the busiest route?", interface_language="en")

        self.assertEqual(airline["intent"], "TOP_AIRLINE")
        self.assertEqual(airport["intent"], "TOP_AIRPORT")
        self.assertEqual(route["intent"], "TOP_ROUTE")

        self.assertGreaterEqual(len(airline["records"]), 1)
        self.assertGreaterEqual(len(airport["records"]), 1)
        self.assertGreaterEqual(len(route["records"]), 1)

    def test_flights_by_status_and_airline_are_database_based(self):
        by_status = self.service.handle_message("Show in air flights", interface_language="en")
        by_airline = self.service.handle_message("Show flights for Alpha Airways", interface_language="en")

        self.assertEqual(by_status["intent"], "FLIGHTS_BY_STATUS")
        self.assertEqual(by_status["metrics"]["in_air_count"], 1)
        self.assertEqual(by_status["records"][0]["flight_number"], "BW303")

        self.assertEqual(by_airline["intent"], "FLIGHTS_BY_AIRLINE")
        self.assertEqual(by_airline["metrics"]["total_flights"], 2)

    def test_database_dictionary_describes_project_tables(self):
        response = self.service.handle_message("Explain the database structure", interface_language="en")

        self.assertEqual(response["intent"], "DATABASE_DICTIONARY")
        self.assertEqual(response["metrics"]["total_flights"], 4)
        self.assertEqual(response["metrics"]["total_logs"], 2)
        self.assertEqual(len(response["records"]), 4)

    def test_unknown_question_returns_out_of_scope_response(self):
        response = self.service.handle_message("Tell me a joke", interface_language="en")

        self.assertEqual(response["type"], "out_of_scope")
        self.assertEqual(response["intent"], COPILOT_INTENTS["UNKNOWN"])
        self.assertGreaterEqual(len(response["suggested_prompts"]), 1)


class CopilotAskViewTests(CopilotTestDataMixin, TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.rewrite_patch = patch(
            "apps.copilot.services.copilot_service.CopilotAnswerRewriter.rewrite",
            return_value=SimpleNamespace(
                ok=False,
                text="",
                error="rewriter disabled during tests",
            ),
        )
        self.rewrite_patch.start()
        self.addCleanup(self.rewrite_patch.stop)

    def test_post_rejects_invalid_json_body(self):
        request = self.factory.post(
            "/copilot/ask/",
            data="{invalid-json",
            content_type="application/json",
        )

        response = CopilotAskView.as_view()(request)
        payload = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 400)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "Invalid JSON body.")

    def test_post_rejects_empty_message(self):
        request = self.factory.post(
            "/copilot/ask/",
            data=json.dumps({"message": "   ", "language": "en"}),
            content_type="application/json",
        )

        response = CopilotAskView.as_view()(request)
        payload = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 400)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "The 'message' field is required.")

    def test_post_returns_database_based_copilot_payload(self):
        request = self.factory.post(
            "/copilot/ask/",
            data=json.dumps({"message": "Show delayed flights", "language": "en-US"}),
            content_type="application/json",
        )

        response = CopilotAskView.as_view()(request)
        payload = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["intent"], COPILOT_INTENTS["DELAYED_FLIGHTS"])
        self.assertEqual(payload["data"]["metrics"]["delayed_count"], 1)

    def test_language_normalization_accepts_french_and_russian_prefixes(self):
        view = CopilotAskView()

        self.assertEqual(view._normalize_language("fr-FR"), "fr")
        self.assertEqual(view._normalize_language("ru_RU"), "ru")
        self.assertEqual(view._normalize_language("en-US"), "en")
        self.assertIsNone(view._normalize_language("de-DE"))