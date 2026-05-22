from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.aircraft.models import Aircraft
from apps.airlines.models import Airline
from apps.airports.models import Airport
from apps.dashboard import views
from apps.flights.models import Flight


class DashboardTestDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="dashboard-tester",
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

        cls.aircraft_alpha = Aircraft.objects.create(
            airline=cls.airline_alpha,
            model="Airbus A320",
            registration_number="EW-DASH",
            aircraft_type="A320",
            capacity=180,
            status="active",
        )

        now = timezone.now()

        cls.flight_scheduled = Flight.objects.create(
            flight_number="DB100",
            airline=cls.airline_alpha,
            aircraft=cls.aircraft_alpha,
            origin_airport=cls.minsk,
            destination_airport=cls.paris,
            scheduled_departure=now + timezone.timedelta(hours=2),
            scheduled_arrival=now + timezone.timedelta(hours=5),
            status="scheduled",
            source_type="local",
        )

        cls.flight_boarding = Flight.objects.create(
            flight_number="DB101",
            airline=cls.airline_alpha,
            aircraft=cls.aircraft_alpha,
            origin_airport=cls.minsk,
            destination_airport=cls.berlin,
            scheduled_departure=now + timezone.timedelta(minutes=50),
            scheduled_arrival=now + timezone.timedelta(hours=2),
            status="boarding",
            source_type="local",
        )

        cls.flight_departed = Flight.objects.create(
            flight_number="DB102",
            airline=cls.airline_alpha,
            aircraft=cls.aircraft_alpha,
            origin_airport=cls.minsk,
            destination_airport=cls.paris,
            scheduled_departure=now - timezone.timedelta(minutes=40),
            scheduled_arrival=now + timezone.timedelta(hours=2),
            status="departed",
            source_type="api",
        )

        cls.flight_in_air_1 = Flight.objects.create(
            flight_number="DB103",
            airline=cls.airline_beta,
            aircraft=None,
            origin_airport=cls.paris,
            destination_airport=cls.minsk,
            scheduled_departure=now - timezone.timedelta(hours=1),
            scheduled_arrival=now + timezone.timedelta(hours=2),
            status="in_air",
            source_type="api",
            live_latitude=51.000000,
            live_longitude=12.000000,
        )

        cls.flight_in_air_2 = Flight.objects.create(
            flight_number="DB104",
            airline=cls.airline_beta,
            aircraft=None,
            origin_airport=cls.paris,
            destination_airport=cls.berlin,
            scheduled_departure=now - timezone.timedelta(hours=1),
            scheduled_arrival=now + timezone.timedelta(hours=1),
            status="in_air",
            source_type="api",
            live_latitude=50.000000,
            live_longitude=11.000000,
        )

        cls.flight_landed = Flight.objects.create(
            flight_number="DB105",
            airline=cls.airline_beta,
            aircraft=None,
            origin_airport=cls.berlin,
            destination_airport=cls.paris,
            scheduled_departure=now - timezone.timedelta(hours=6),
            scheduled_arrival=now - timezone.timedelta(hours=4),
            actual_arrival=now - timezone.timedelta(hours=4),
            status="landed",
            source_type="local",
        )

        cls.flight_delayed = Flight.objects.create(
            flight_number="DB106",
            airline=cls.airline_alpha,
            aircraft=cls.aircraft_alpha,
            origin_airport=cls.minsk,
            destination_airport=cls.paris,
            scheduled_departure=now - timezone.timedelta(hours=2),
            scheduled_arrival=now + timezone.timedelta(hours=1),
            actual_departure=now - timezone.timedelta(hours=1),
            status="delayed",
            source_type="api",
        )

        cls.flight_cancelled = Flight.objects.create(
            flight_number="DB107",
            airline=cls.airline_beta,
            aircraft=None,
            origin_airport=cls.paris,
            destination_airport=cls.berlin,
            scheduled_departure=now + timezone.timedelta(hours=3),
            scheduled_arrival=now + timezone.timedelta(hours=5),
            status="cancelled",
            source_type="local",
        )


class DashboardHelperTests(TestCase):
    def test_safe_rate_handles_zero_and_regular_percentages(self):
        self.assertEqual(views.safe_rate(0, 0), 0)
        self.assertEqual(views.safe_rate(2, 4), 50.0)
        self.assertEqual(views.safe_rate(1, 3), 33.3)

    def test_status_label_returns_known_and_fallback_label(self):
        self.assertEqual(str(views.get_status_label("scheduled")), "Scheduled")
        self.assertEqual(str(views.get_status_label("boarding")), "Boarding")
        self.assertEqual(str(views.get_status_label("departed")), "Departed")
        self.assertEqual(str(views.get_status_label("in_air")), "In Air")
        self.assertEqual(str(views.get_status_label("landed")), "Landed")
        self.assertEqual(str(views.get_status_label("delayed")), "Delayed")
        self.assertEqual(str(views.get_status_label("cancelled")), "Cancelled")
        self.assertEqual(views.get_status_label("unknown_status"), "Unknown Status")

    def test_route_label_handles_missing_route_data(self):
        self.assertEqual(str(views.get_route_label(None)), "No route data")

        label = views.get_route_label(
            {
                "origin_airport__iata_code": "MSQ",
                "destination_airport__iata_code": "CDG",
            }
        )

        self.assertEqual(label, "MSQ → CDG")

    def test_high_risk_count_is_conservative_placeholder(self):
        self.assertEqual(views.get_high_risk_count(), 0)


class DashboardSnapshotBusinessTests(DashboardTestDataMixin, TestCase):
    def test_status_counts_are_grouped_by_business_status(self):
        counts = views.get_status_counts()

        self.assertEqual(counts["scheduled_count"], 1)
        self.assertEqual(counts["boarding_count"], 1)
        self.assertEqual(counts["departed_count"], 1)
        self.assertEqual(counts["in_air_count"], 2)
        self.assertEqual(counts["landed_count"], 1)
        self.assertEqual(counts["delayed_count"], 1)
        self.assertEqual(counts["cancelled_count"], 1)

    def test_global_operational_snapshot_calculates_dashboard_metrics(self):
        snapshot = views.get_global_operational_snapshot()

        self.assertEqual(snapshot["total_flights"], 8)
        self.assertEqual(snapshot["total_airlines"], 2)
        self.assertEqual(snapshot["total_airports"], 3)
        self.assertEqual(snapshot["total_aircraft"], 1)

        self.assertEqual(snapshot["scheduled_count"], 1)
        self.assertEqual(snapshot["boarding_count"], 1)
        self.assertEqual(snapshot["departed_count"], 1)
        self.assertEqual(snapshot["in_air_count"], 2)
        self.assertEqual(snapshot["landed_count"], 1)
        self.assertEqual(snapshot["delayed_count"], 1)
        self.assertEqual(snapshot["cancelled_count"], 1)

        self.assertEqual(snapshot["active_flights"], 6)
        self.assertEqual(snapshot["api_flights"], 4)
        self.assertEqual(snapshot["local_flights"], 4)

        self.assertEqual(snapshot["critical_count"], 1)
        self.assertEqual(snapshot["attention_count"], 1)
        self.assertEqual(snapshot["irregular_ops_count"], 2)
        self.assertEqual(snapshot["stable_count"], 2)

        self.assertEqual(snapshot["delay_rate"], 12.5)
        self.assertEqual(snapshot["cancellation_rate"], 12.5)
        self.assertEqual(snapshot["active_rate"], 75.0)
        self.assertEqual(snapshot["api_rate"], 50.0)
        self.assertEqual(snapshot["local_rate"], 50.0)

        self.assertIsNotNone(snapshot["most_active_airline"])
        self.assertIsNotNone(snapshot["most_used_route"])
        self.assertIn("→", snapshot["most_used_route_label"])
        self.assertIn(
            str(snapshot["source_mode"]),
            ["API-led dataset", "Local-led dataset", "Balanced sources"],
        )

    def test_preview_flights_only_keeps_routes_with_coordinates(self):
        preview = views.build_preview_flights(limit=20)

        self.assertEqual(len(preview), 8)

        first_item = preview[0]

        expected_keys = {
            "flight_number",
            "airline",
            "status",
            "status_display",
            "origin_code",
            "destination_code",
            "origin_lat",
            "origin_lng",
            "destination_lat",
            "destination_lng",
        }

        self.assertEqual(set(first_item.keys()), expected_keys)
        self.assertIsInstance(first_item["origin_lat"], float)
        self.assertIsInstance(first_item["destination_lng"], float)

    def test_ranked_flights_prioritize_cancelled_and_delayed_records(self):
        ranked = list(views.get_ranked_flights(limit=3, include_source_bonus=True))

        self.assertEqual(ranked[0].status, "cancelled")
        self.assertEqual(ranked[1].status, "delayed")
        self.assertGreaterEqual(ranked[0].priority_score, ranked[1].priority_score)

    def test_recent_flights_returns_recent_business_records(self):
        recent = list(views.get_recent_flights(limit=4))

        self.assertEqual(len(recent), 4)
        self.assertTrue(all(isinstance(flight, Flight) for flight in recent))

    def test_command_insights_summarize_recovery_delay_airline_route_and_source(self):
        snapshot = views.get_global_operational_snapshot()
        insights = views.build_command_insights(snapshot)

        self.assertGreaterEqual(len(insights), 1)
        self.assertLessEqual(len(insights), 4)

        combined = " ".join(str(item) for item in insights).lower()

        self.assertTrue(
            "critical" in combined
            or "cancelled" in combined
            or "delayed" in combined
            or "airline" in combined
            or "route" in combined
        )


class DashboardAlertContextTests(DashboardTestDataMixin, TestCase):
    def test_alert_context_returns_medium_when_attention_pressure_is_visible(self):
        snapshot = views.get_global_operational_snapshot()
        alert_context = views.get_operational_alert_context(snapshot)

        self.assertIn(str(alert_context["operational_alert_level"]), ["Normal", "Medium", "High"])
        self.assertIn(
            str(alert_context["dashboard_mode"]),
            [
                "Standard Control",
                "Recovery Supervision",
                "Elevated Supervision",
                "Live Traffic Monitoring",
                "Low Activity",
            ],
        )
        self.assertIn("priority_focus", alert_context)
        self.assertEqual(alert_context["cancelled_count_for_alert"], 1)
        self.assertEqual(alert_context["delayed_count_for_alert"], 1)

    def test_alert_context_returns_high_for_heavy_recovery_pressure(self):
        now = timezone.now()

        Flight.objects.create(
            flight_number="DB900",
            airline=self.airline_alpha,
            aircraft=self.aircraft_alpha,
            origin_airport=self.minsk,
            destination_airport=self.paris,
            scheduled_departure=now + timezone.timedelta(hours=7),
            scheduled_arrival=now + timezone.timedelta(hours=9),
            status="cancelled",
            source_type="local",
        )

        Flight.objects.create(
            flight_number="DB901",
            airline=self.airline_alpha,
            aircraft=self.aircraft_alpha,
            origin_airport=self.minsk,
            destination_airport=self.berlin,
            scheduled_departure=now + timezone.timedelta(hours=8),
            scheduled_arrival=now + timezone.timedelta(hours=10),
            status="cancelled",
            source_type="local",
        )

        snapshot = views.get_global_operational_snapshot()
        alert_context = views.get_operational_alert_context(snapshot)

        self.assertEqual(str(alert_context["operational_alert_level"]), "High")
        self.assertEqual(str(alert_context["dashboard_mode"]), "Recovery Supervision")

    def test_alert_context_returns_low_activity_when_no_active_flights_exist(self):
        Flight.objects.exclude(status="landed").delete()

        snapshot = views.get_global_operational_snapshot()
        alert_context = views.get_operational_alert_context(snapshot)

        self.assertEqual(str(alert_context["dashboard_mode"]), "Low Activity")


class DashboardViewsTests(DashboardTestDataMixin, TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_public_home_view_builds_public_operational_context(self):
        request = self.factory.get("/")

        with patch("apps.dashboard.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.public_home_view(request)

            self.assertEqual(response.status_code, 200)

            template_name = mocked_render.call_args.args[1]
            context = mocked_render.call_args.args[2]

            self.assertEqual(template_name, "home.html")
            self.assertEqual(context["total_flights"], 8)
            self.assertGreaterEqual(len(context["public_highlights"]), 1)
            self.assertEqual(len(context["preview_flights"]), 8)
            self.assertGreaterEqual(len(context["recent_flights"]), 1)

    def test_private_dashboard_view_builds_command_center_context(self):
        request = self.factory.get("/dashboard/")
        request.user = self.user

        with patch("apps.dashboard.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.private_dashboard_view(request)

            self.assertEqual(response.status_code, 200)

            template_name = mocked_render.call_args.args[1]
            context = mocked_render.call_args.args[2]

            self.assertEqual(template_name, "dashboard/dashboard.html")
            self.assertEqual(context["total_flights"], 8)
            self.assertIn("operational_alert_level", context)
            self.assertIn("dashboard_mode", context)
            self.assertIn("priority_focus", context)
            self.assertGreaterEqual(len(context["recent_flights"]), 1)
            self.assertGreaterEqual(len(context["priority_flights"]), 1)
            self.assertGreaterEqual(len(context["command_insights"]), 1)