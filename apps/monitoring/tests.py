import json
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.aircraft.models import Aircraft
from apps.airlines.models import Airline
from apps.airports.models import Airport
from apps.flights.models import Flight, FlightStatusHistory
from apps.monitoring import services
from apps.monitoring.views import (
    map_view,
    monitoring_alerts_view,
    monitoring_critical_view,
    monitoring_flight_detail_view,
    monitoring_home,
    monitoring_live_view,
    weather_hazards_api,
)


class MonitoringTestDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="monitoring-tester",
            password="test-password",
        )

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
            registration_number="EW-MONITOR",
            aircraft_type="A320",
            capacity=180,
            status="active",
        )

        now = timezone.now()

        cls.cancelled_flight = Flight.objects.create(
            flight_number="AA900",
            airline=cls.airline_alpha,
            aircraft=cls.aircraft,
            origin_airport=cls.minsk,
            destination_airport=cls.paris,
            scheduled_departure=now + timezone.timedelta(hours=1),
            scheduled_arrival=now + timezone.timedelta(hours=4),
            status="cancelled",
            source_type="local",
        )

        cls.delayed_flight = Flight.objects.create(
            flight_number="AA901",
            airline=cls.airline_alpha,
            aircraft=cls.aircraft,
            origin_airport=cls.minsk,
            destination_airport=cls.berlin,
            scheduled_departure=now - timezone.timedelta(hours=2),
            scheduled_arrival=now + timezone.timedelta(hours=1),
            actual_departure=now - timezone.timedelta(hours=1),
            status="delayed",
            source_type="api",
            external_id="EXT-AA901",
            live_latitude=52.000000,
            live_longitude=20.000000,
            live_speed=430,
            live_altitude=9000,
            live_direction=120,
        )

        cls.in_air_flight = Flight.objects.create(
            flight_number="BW700",
            airline=cls.airline_beta,
            aircraft=None,
            origin_airport=cls.paris,
            destination_airport=cls.minsk,
            scheduled_departure=now - timezone.timedelta(hours=1),
            scheduled_arrival=now + timezone.timedelta(hours=2),
            status="in_air",
            source_type="api",
            external_id="EXT-BW700",
            live_latitude=51.000000,
            live_longitude=12.000000,
            live_speed=760,
            live_altitude=11000,
            live_direction=75,
        )

        cls.boarding_flight = Flight.objects.create(
            flight_number="BW701",
            airline=cls.airline_beta,
            aircraft=None,
            origin_airport=cls.berlin,
            destination_airport=cls.paris,
            scheduled_departure=now + timezone.timedelta(minutes=40),
            scheduled_arrival=now + timezone.timedelta(hours=2),
            status="boarding",
            source_type="local",
        )

        cls.landed_flight = Flight.objects.create(
            flight_number="AA100",
            airline=cls.airline_alpha,
            aircraft=cls.aircraft,
            origin_airport=cls.paris,
            destination_airport=cls.berlin,
            scheduled_departure=now - timezone.timedelta(hours=5),
            scheduled_arrival=now - timezone.timedelta(hours=3),
            actual_arrival=now - timezone.timedelta(hours=3),
            status="landed",
            source_type="local",
        )

        FlightStatusHistory.objects.create(
            flight=cls.delayed_flight,
            previous_status="scheduled",
            new_status="delayed",
            change_type="status",
            source_type_snapshot="api",
            is_disruption_event=True,
            status_changed=True,
            live_data_changed=True,
            departure_delay_minutes=60,
            change_summary="Delay detected from API feed.",
        )

        FlightStatusHistory.objects.create(
            flight=cls.cancelled_flight,
            previous_status="scheduled",
            new_status="cancelled",
            change_type="status",
            source_type_snapshot="local",
            is_disruption_event=True,
            status_changed=True,
            change_summary="Cancellation registered.",
        )

    def authenticated_request(self, method="get", path="/monitoring/", data=None, body=None, content_type=None):
        factory = RequestFactory()

        if method == "post":
            request = factory.post(
                path,
                data=body if body is not None else data,
                content_type=content_type,
            )
        else:
            request = factory.get(path, data=data or {})

        request.user = self.user
        return request


class MonitoringServicePrimitiveTests(MonitoringTestDataMixin, TestCase):
    def test_haversine_returns_realistic_distance_between_known_airports(self):
        distance = services.haversine_km(
            float(self.minsk.latitude),
            float(self.minsk.longitude),
            float(self.paris.latitude),
            float(self.paris.longitude),
        )

        self.assertGreater(distance, 1800)
        self.assertLess(distance, 2200)

    def test_progress_by_status_maps_operational_lifecycle(self):
        self.assertEqual(services.get_progress_by_status("scheduled"), 0.10)
        self.assertEqual(services.get_progress_by_status("boarding"), 0.22)
        self.assertEqual(services.get_progress_by_status("in_air"), 0.68)
        self.assertEqual(services.get_progress_by_status("landed"), 1.0)
        self.assertEqual(services.get_progress_by_status("cancelled"), 0.0)
        self.assertEqual(services.get_progress_by_status("unknown"), 0.10)

    def test_source_display_and_label_helpers_are_stable(self):
        self.assertEqual(str(services.get_source_display("api")), "API")
        self.assertEqual(str(services.get_source_display("local")), "Local")
        self.assertEqual(str(services.get_source_display("other")), "Unknown")

        self.assertEqual(str(services.get_airport_code(self.minsk)), "MSQ")
        self.assertEqual(str(services.get_airport_name(self.minsk)), "Minsk National Airport")
        self.assertEqual(str(services.get_aircraft_display(self.aircraft)), "Airbus A320")
        self.assertEqual(str(services.get_aircraft_registration(self.aircraft)), "EW-MONITOR")

    def test_risk_level_normalization(self):
        self.assertEqual(services.get_risk_level(90), "High Risk")
        self.assertEqual(services.get_risk_level(50), "Medium Risk")
        self.assertEqual(services.get_risk_level(20), "Low Risk")

        self.assertEqual(services.normalize_risk_level_key("High Risk"), "high")
        self.assertEqual(services.normalize_risk_level_key("Medium Risk"), "medium")
        self.assertEqual(services.normalize_risk_level_key("Low Risk"), "low")

    def test_route_alert_normalization(self):
        self.assertEqual(services.normalize_route_alert_key("Critical Corridor"), "critical")
        self.assertEqual(services.normalize_route_alert_key("Disrupted Corridor"), "operational")
        self.assertEqual(services.normalize_route_alert_key("Sensitive Corridor"), "attention")
        self.assertEqual(services.normalize_route_alert_key("Active Corridor"), "attention")
        self.assertEqual(services.normalize_route_alert_key("Normal Corridor"), "clear")


class MonitoringTrackingAndRiskTests(MonitoringTestDataMixin, TestCase):
    def test_tracking_confidence_is_estimated_without_live_position(self):
        meta = services.compute_tracking_confidence(self.cancelled_flight)

        self.assertEqual(meta["tracking_confidence"], "estimated")
        self.assertEqual(meta["tracking_confidence_score"], 0)
        self.assertFalse(meta["is_live_confirmed"])
        self.assertIsNone(meta["live_freshness_minutes"])

    def test_tracking_confidence_is_high_for_api_live_external_flight(self):
        meta = services.compute_tracking_confidence(self.in_air_flight)

        self.assertEqual(meta["tracking_confidence"], "high")
        self.assertEqual(meta["tracking_confidence_score"], 100)
        self.assertTrue(meta["is_live_confirmed"])
        self.assertFalse(meta["is_live_low_confidence"])
        self.assertIsNotNone(meta["live_freshness_minutes"])

    def test_tracking_confidence_is_low_when_live_coordinates_have_no_external_match(self):
        self.in_air_flight.external_id = ""
        self.in_air_flight.save(update_fields=["external_id"])

        meta = services.compute_tracking_confidence(self.in_air_flight)

        self.assertEqual(meta["tracking_confidence"], "low")
        self.assertEqual(meta["tracking_confidence_score"], 35)
        self.assertTrue(meta["is_live_low_confidence"])

    def test_compute_risk_score_prioritizes_cancelled_flights_as_high_risk(self):
        progress = services.get_progress_by_status(self.cancelled_flight.status)
        tracking_meta = services.compute_tracking_confidence(self.cancelled_flight)
        history = services.get_history_summary(self.cancelled_flight)

        score = services.compute_risk_score(
            flight=self.cancelled_flight,
            progress=progress,
            has_live_position=False,
            tracking_meta=tracking_meta,
            history=history,
        )

        self.assertGreaterEqual(score, 82)
        self.assertEqual(services.get_risk_level(score), "High Risk")

    def test_compute_operational_profile_returns_posture_from_status_and_risk(self):
        cancelled_profile = services.compute_operational_profile(self.cancelled_flight)
        delayed_profile = services.compute_operational_profile(self.delayed_flight)
        in_air_profile = services.compute_operational_profile(self.in_air_flight)

        self.assertEqual(cancelled_profile["posture"], "critical")
        self.assertIn(cancelled_profile["risk_level_key"], ["high", "medium", "low"])

        self.assertIn(delayed_profile["posture"], ["attention", "critical"])
        self.assertIn(delayed_profile["risk_level_key"], ["medium", "high"])

        self.assertIn(in_air_profile["posture"], ["normal", "attention", "critical"])
        self.assertIn("tracking_meta", in_air_profile)
        self.assertIn("history", in_air_profile)


class MonitoringSnapshotAndQueueTests(MonitoringTestDataMixin, TestCase):
    def test_monitoring_snapshot_calculates_core_business_indicators(self):
        flights = services.get_monitoring_base_queryset()
        snapshot = services.get_monitoring_snapshot(flights)

        self.assertEqual(snapshot["total_flights"], 5)
        self.assertEqual(snapshot["cancelled_count"], 1)
        self.assertEqual(snapshot["delayed_count"], 1)
        self.assertEqual(snapshot["in_air_count"], 1)
        self.assertEqual(snapshot["boarding_count"], 1)
        self.assertEqual(snapshot["landed_count"], 1)

        self.assertEqual(snapshot["api_count"], 2)
        self.assertEqual(snapshot["local_count"], 3)

        self.assertEqual(snapshot["delay_rate"], 20.0)
        self.assertEqual(snapshot["cancellation_rate"], 20.0)
        self.assertGreater(snapshot["active_rate"], 0)

        self.assertGreaterEqual(snapshot["critical_count"], 1)
        self.assertGreaterEqual(snapshot["attention_count"], 1)
        self.assertIn(snapshot["alert_level"], ["Normal", "Medium", "High"])
        self.assertGreaterEqual(len(snapshot["recommendations"]), 1)

    def test_attention_queue_orders_operationally_sensitive_flights_first(self):
        flights = services.get_monitoring_base_queryset()
        queue = services.build_attention_queue(flights, limit=5)

        self.assertEqual(len(queue), 5)
        self.assertEqual(queue[0]["flight"].flight_number, "AA900")
        self.assertGreaterEqual(queue[0]["priority"], queue[-1]["priority"])
        self.assertEqual(str(queue[0]["attention_label"]), "Immediate Action")

    def test_monitoring_reason_and_next_label_follow_status(self):
        self.assertIn("cancelled", str(services.get_flight_monitoring_reason(self.cancelled_flight)).lower())
        self.assertEqual(str(services.get_attention_label(self.cancelled_flight)), "Immediate Action")

        self.assertIn("delayed", str(services.get_flight_monitoring_reason(self.delayed_flight)).lower())
        self.assertEqual(str(services.get_attention_label(self.delayed_flight)), "Attention Review")

        self.assertEqual(str(services.get_attention_label(self.in_air_flight)), "Live Tracking")
        self.assertEqual(str(services.get_attention_label(self.boarding_flight)), "Departure Control")


class MonitoringActionEngineTests(MonitoringTestDataMixin, TestCase):
    def test_next_operational_action_changes_by_status_and_tracking_quality(self):
        estimated_meta = services.compute_tracking_confidence(self.cancelled_flight)
        live_meta = services.compute_tracking_confidence(self.in_air_flight)

        self.assertIn(
            "recovery",
            str(
                services.build_next_operational_action(
                    self.cancelled_flight,
                    "High Risk",
                    estimated_meta,
                )
            ).lower(),
        )

        self.assertIn(
            "arrival",
            str(
                services.build_next_operational_action(
                    self.in_air_flight,
                    "Low Risk",
                    live_meta,
                )
            ).lower(),
        )

    def test_operational_recommendation_explains_cancelled_delayed_and_landed_cases(self):
        cancelled_meta = services.compute_tracking_confidence(self.cancelled_flight)
        delayed_meta = services.compute_tracking_confidence(self.delayed_flight)
        landed_meta = services.compute_tracking_confidence(self.landed_flight)

        cancelled_note = services.build_operational_recommendation(
            self.cancelled_flight,
            "High Risk",
            0,
            cancelled_meta,
        )
        delayed_note = services.build_operational_recommendation(
            self.delayed_flight,
            "Medium Risk",
            500,
            delayed_meta,
        )
        landed_note = services.build_operational_recommendation(
            self.landed_flight,
            "Low Risk",
            0,
            landed_meta,
        )

        self.assertIn("Recovery", str(cancelled_note))
        self.assertIn("delay", str(delayed_note).lower())
        self.assertIn("completed", str(landed_note).lower())

    def test_action_engine_returns_decision_fields_for_cancelled_and_in_air(self):
        cancelled_meta = services.compute_tracking_confidence(self.cancelled_flight)
        in_air_meta = services.compute_tracking_confidence(self.in_air_flight)

        cancelled_action = services.build_action_engine(
            flight=self.cancelled_flight,
            risk_level="High Risk",
            tracking_meta=cancelled_meta,
            remaining_km=0,
            eta=None,
        )

        in_air_action = services.build_action_engine(
            flight=self.in_air_flight,
            risk_level="Medium Risk",
            tracking_meta=in_air_meta,
            remaining_km=350,
            eta=timezone.now() + timezone.timedelta(hours=1),
        )

        self.assertEqual(cancelled_action["action_priority_key"], "immediate")
        self.assertEqual(str(cancelled_action["command_tag"]), "Recover")

        self.assertEqual(in_air_action["action_priority_key"], "attention")
        self.assertIn(str(in_air_action["command_tag"]), ["Monitor", "Track", "Control"])

    def test_estimate_eta_handles_cancelled_landed_live_speed_and_schedule(self):
        self.assertIsNone(
            services.estimate_eta(
                self.cancelled_flight,
                remaining_km=100,
                progress=0.5,
            )
        )

        landed_eta = services.estimate_eta(
            self.landed_flight,
            remaining_km=0,
            progress=1,
        )
        self.assertEqual(landed_eta, self.landed_flight.actual_arrival or self.landed_flight.scheduled_arrival)

        live_eta = services.estimate_eta(
            self.in_air_flight,
            remaining_km=760,
            progress=0.68,
        )
        self.assertIsNotNone(live_eta)


class MonitoringMapPayloadTests(MonitoringTestDataMixin, TestCase):
    def fake_reverse(self, name, args=None, kwargs=None):
        args = args or []

        if name == "monitoring:monitoring_home":
            return "/monitoring/"

        if name == "flights:flight_detail":
            return f"/flights/{args[0]}/"

        if name == "monitoring:monitoring_flight_detail":
            return f"/monitoring/flights/{args[0]}/"

        return f"/{name}/"

    def test_map_flight_payload_contains_business_map_contract(self):
        with patch("apps.monitoring.services.reverse", side_effect=self.fake_reverse):
            payload = services.build_map_flight_payload(self.in_air_flight)

        expected_keys = {
            "flight_number",
            "airline",
            "status",
            "source_type",
            "origin_code",
            "destination_code",
            "origin_lat",
            "origin_lng",
            "destination_lat",
            "destination_lng",
            "live_lat",
            "live_lng",
            "progress",
            "total_distance_km",
            "remaining_distance_km",
            "risk_score",
            "risk_level",
            "risk_level_display",
            "route_alert",
            "priority",
            "tracking_confidence",
            "recommendation",
            "next_action",
            "action_required",
            "map_priority_score",
            "detail_url",
            "monitoring_url",
            "monitoring_detail_url",
        }

        for key in expected_keys:
            self.assertIn(key, payload)

        self.assertEqual(payload["flight_number"], "BW700")
        self.assertEqual(payload["status"], "in_air")
        self.assertEqual(payload["source_type"], "api")
        self.assertEqual(payload["origin_code"], "CDG")
        self.assertEqual(payload["destination_code"], "MSQ")
        self.assertGreater(payload["total_distance_km"], 0)
        self.assertGreaterEqual(payload["risk_score"], 0)
        self.assertLessEqual(payload["risk_score"], 100)

    def test_map_supervision_meta_detects_elevated_or_crisis_pressure(self):
        flights_list = [
            {
                "status": "cancelled",
                "risk_level": "high",
                "risk_level_display": "High Risk",
                "disruption_score": 35,
            },
            {
                "status": "delayed",
                "risk_level": "medium",
                "risk_level_display": "Medium Risk",
                "disruption_score": 20,
            },
            {
                "status": "in_air",
                "risk_level": "low",
                "risk_level_display": "Low Risk",
                "disruption_score": 1,
            },
        ]

        meta = services.compute_map_supervision_meta(flights_list)

        self.assertEqual(meta["map_total_mapped"], 3)
        self.assertEqual(meta["map_cancelled_count"], 1)
        self.assertEqual(meta["map_delayed_count"], 1)
        self.assertEqual(meta["map_in_air_count"], 1)
        self.assertEqual(meta["map_high_risk_count"], 1)
        self.assertEqual(meta["map_medium_risk_count"], 1)
        self.assertEqual(meta["map_critical_count"], 1)
        self.assertEqual(meta["map_attention_count"], 1)
        self.assertEqual(meta["map_disruption_score"], 56)
        self.assertIn(meta["map_supervision_mode_key"], ["stable", "elevated", "crisis"])

    def test_build_map_context_serializes_all_valid_mapped_flights(self):
        flights = services.get_monitoring_base_queryset().exclude(
            origin_airport__latitude__isnull=True
        )

        with patch("apps.monitoring.services.reverse", side_effect=self.fake_reverse):
            context = services.build_map_context(
                flights=flights,
                selected_flight_id=self.in_air_flight.id,
            )

        self.assertEqual(context["selected_flight_id"], str(self.in_air_flight.id))
        self.assertEqual(context["map_total_mapped"], 5)
        self.assertEqual(len(context["map_flights"]), 5)
        self.assertEqual(context["map_flights"], context["map_flights_json"])
        self.assertEqual(context["map_flights"], context["flights_json"])


class MonitoringViewTests(MonitoringTestDataMixin, TestCase):
    def test_monitoring_home_filters_by_query_status_source_and_selected_flight(self):
        request = self.authenticated_request(
            path="/monitoring/",
            data={
                "q": "AA901",
                "status": "delayed",
                "source": "api",
                "flight": str(self.delayed_flight.id),
            },
        )

        with patch("apps.monitoring.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = monitoring_home(request)

            self.assertEqual(response.status_code, 200)

            template_name = mocked_render.call_args.args[1]
            context = mocked_render.call_args.args[2]

            self.assertEqual(template_name, "monitoring/index.html")
            self.assertEqual(context["selected_flight"], self.delayed_flight)
            self.assertEqual(context["search_query"], "AA901")
            self.assertEqual(context["selected_status"], "delayed")
            self.assertEqual(context["selected_source"], "api")
            self.assertEqual(context["total_flights"], 1)
            self.assertEqual(context["delayed_count"], 1)
            self.assertGreaterEqual(len(context["attention_queue"]), 1)

    def test_monitoring_critical_view_returns_cancelled_filter_context(self):
        request = self.authenticated_request(
            path="/monitoring/critical/",
            data={"status": "cancelled"},
        )

        with patch("apps.monitoring.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = monitoring_critical_view(request)

            self.assertEqual(response.status_code, 200)

            template_name = mocked_render.call_args.args[1]
            context = mocked_render.call_args.args[2]

            self.assertEqual(template_name, "monitoring/critical.html")
            self.assertEqual(context["selected_status"], "cancelled")
            self.assertGreaterEqual(context["critical_count"], 1)
            self.assertEqual(context["cancelled_count"], 1)
            self.assertIn(context["alert_level"], ["Normal", "Medium", "High"])

    def test_monitoring_alerts_view_builds_alerts_from_snapshot(self):
        request = self.authenticated_request(path="/monitoring/alerts/")

        with patch("apps.monitoring.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = monitoring_alerts_view(request)

            self.assertEqual(response.status_code, 200)

            template_name = mocked_render.call_args.args[1]
            context = mocked_render.call_args.args[2]

            self.assertEqual(template_name, "monitoring/alerts.html")
            self.assertIn("alerts", context)
            self.assertGreaterEqual(len(context["alerts"]), 1)

            alert_titles = [str(alert["title"]) for alert in context["alerts"]]
            self.assertTrue(
                any(
                    "Cancelled" in title
                    or "Attention" in title
                    or "Critical" in title
                    or "External" in title
                    for title in alert_titles
                )
            )

    def test_monitoring_live_view_counts_active_execution_states(self):
        request = self.authenticated_request(path="/monitoring/live/")

        with patch("apps.monitoring.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = monitoring_live_view(request)

            self.assertEqual(response.status_code, 200)

            template_name = mocked_render.call_args.args[1]
            context = mocked_render.call_args.args[2]

            self.assertEqual(template_name, "monitoring/live.html")
            self.assertEqual(context["live_count"], 2)
            self.assertEqual(context["boarding_count"], 1)
            self.assertEqual(context["in_air_count"], 1)
            self.assertEqual(context["departed_count"], 0)
            self.assertEqual(context["api_count"], 1)
            self.assertEqual(context["local_count"], 1)

    def test_monitoring_flight_detail_view_builds_risk_and_history_context(self):
        request = self.authenticated_request(
            path=f"/monitoring/flights/{self.delayed_flight.id}/"
        )

        with patch("apps.monitoring.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = monitoring_flight_detail_view(request, pk=self.delayed_flight.id)

            self.assertEqual(response.status_code, 200)

            template_name = mocked_render.call_args.args[1]
            context = mocked_render.call_args.args[2]

            self.assertEqual(template_name, "monitoring/flight_detail.html")
            self.assertEqual(context["flight"], self.delayed_flight)
            self.assertIn(context["urgency_key"], ["attention", "critical", "normal"])
            self.assertGreaterEqual(context["status_change_events"], 1)
            self.assertGreaterEqual(context["disruption_events"], 1)
            self.assertGreaterEqual(context["risk_score"], 0)
            self.assertIn(context["risk_level"], ["Low Risk", "Medium Risk", "High Risk"])
            self.assertIn("tracking_meta", context)
            self.assertIn("current_operational_note", context)
            self.assertIn("next_operational_action", context)

    def test_map_view_excludes_unmapped_flights_and_passes_weather_key(self):
        request = self.authenticated_request(
            path="/monitoring/map/",
            data={"flight": str(self.in_air_flight.id)},
        )

        def fake_reverse(name, args=None, kwargs=None):
            args = args or []

            if name == "monitoring:monitoring_home":
                return "/monitoring/"

            if name == "flights:flight_detail":
                return f"/flights/{args[0]}/"

            if name == "monitoring:monitoring_flight_detail":
                return f"/monitoring/flights/{args[0]}/"

            return f"/{name}/"

        with patch("apps.monitoring.services.reverse", side_effect=fake_reverse):
            with patch("apps.monitoring.views.render") as mocked_render:
                mocked_render.return_value = SimpleNamespace(status_code=200)

                response = map_view(request)

                self.assertEqual(response.status_code, 200)

                template_name = mocked_render.call_args.args[1]
                context = mocked_render.call_args.args[2]

                self.assertEqual(template_name, "monitoring/map.html")
                self.assertEqual(context["selected_flight_id"], str(self.in_air_flight.id))
                self.assertEqual(context["map_total_mapped"], 5)
                self.assertIn("weather_api_key", context)
                self.assertEqual(len(context["map_flights"]), 5)


class WeatherHazardsApiTests(MonitoringTestDataMixin, TestCase):
    def test_weather_hazards_api_rejects_invalid_json(self):
        request = self.authenticated_request(
            method="post",
            path="/monitoring/weather-hazards/",
            body="{invalid-json",
            content_type="application/json",
        )

        response = weather_hazards_api(request)
        payload = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 400)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "Invalid JSON payload.")

    def test_weather_hazards_api_rejects_non_list_airports(self):
        request = self.authenticated_request(
            method="post",
            path="/monitoring/weather-hazards/",
            body=json.dumps(
                {
                    "airports": {"code": "MSQ"},
                    "operational_summary": {},
                }
            ),
            content_type="application/json",
        )

        response = weather_hazards_api(request)
        payload = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 400)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "Airports must be a list.")

    def test_weather_hazards_api_returns_service_payload(self):
        request = self.authenticated_request(
            method="post",
            path="/monitoring/weather-hazards/",
            body=json.dumps(
                {
                    "airports": [
                        {
                            "code": "MSQ",
                            "lat": 53.8825,
                            "lng": 28.0307,
                        }
                    ],
                    "operational_summary": {
                        "mode": "stable",
                    },
                }
            ),
            content_type="application/json",
        )

        service_payload = {
            "ok": True,
            "hazards": [
                {
                    "airport": "MSQ",
                    "level": "normal",
                }
            ],
        }

        with patch(
            "apps.monitoring.views.WeatherHazardService.build_weather_payload",
            return_value=service_payload,
        ) as mocked_service:
            response = weather_hazards_api(request)
            payload = json.loads(response.content.decode("utf-8"))

            self.assertEqual(response.status_code, 200)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["hazards"][0]["airport"], "MSQ")

            mocked_service.assert_called_once()
            call_kwargs = mocked_service.call_args.kwargs
            self.assertIsInstance(call_kwargs["airports"], list)
            self.assertEqual(call_kwargs["operational_summary"]["mode"], "stable")

    def test_weather_hazards_api_returns_safe_error_when_service_fails(self):
        request = self.authenticated_request(
            method="post",
            path="/monitoring/weather-hazards/",
            body=json.dumps(
                {
                    "airports": [
                        {
                            "code": "CDG",
                            "lat": 49.0097,
                            "lng": 2.5479,
                        }
                    ],
                    "operational_summary": "wrong-type",
                }
            ),
            content_type="application/json",
        )

        with patch(
            "apps.monitoring.views.WeatherHazardService.build_weather_payload",
            side_effect=Exception("weather provider unavailable"),
        ):
            response = weather_hazards_api(request)
            payload = json.loads(response.content.decode("utf-8"))

            self.assertEqual(response.status_code, 500)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["error"], "Weather hazard service failed.")
            self.assertIn("weather provider unavailable", payload["details"])