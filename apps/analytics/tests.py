from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.aircraft.models import Aircraft
from apps.airlines.models import Airline
from apps.airports.models import Airport
from apps.analytics import views
from apps.flights.models import Flight


class AnalyticsTestDataMixin:
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
            registration_number="EW-ANA",
            aircraft_type="A320",
            capacity=180,
            status="active",
        )

        now = timezone.now()

        cls.flight_scheduled = Flight.objects.create(
            flight_number="AN100",
            airline=cls.airline_alpha,
            aircraft=cls.aircraft,
            origin_airport=cls.minsk,
            destination_airport=cls.paris,
            scheduled_departure=now + timezone.timedelta(hours=2),
            scheduled_arrival=now + timezone.timedelta(hours=5),
            status="scheduled",
            source_type="local",
        )

        cls.flight_boarding = Flight.objects.create(
            flight_number="AN101",
            airline=cls.airline_alpha,
            aircraft=cls.aircraft,
            origin_airport=cls.minsk,
            destination_airport=cls.berlin,
            scheduled_departure=now + timezone.timedelta(minutes=40),
            scheduled_arrival=now + timezone.timedelta(hours=2),
            status="boarding",
            source_type="local",
        )

        cls.flight_departed = Flight.objects.create(
            flight_number="AN102",
            airline=cls.airline_alpha,
            aircraft=cls.aircraft,
            origin_airport=cls.minsk,
            destination_airport=cls.paris,
            scheduled_departure=now - timezone.timedelta(minutes=30),
            scheduled_arrival=now + timezone.timedelta(hours=2),
            status="departed",
            source_type="api",
        )

        cls.flight_in_air = Flight.objects.create(
            flight_number="AN103",
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

        cls.flight_landed = Flight.objects.create(
            flight_number="AN104",
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
            flight_number="AN105",
            airline=cls.airline_alpha,
            aircraft=cls.aircraft,
            origin_airport=cls.minsk,
            destination_airport=cls.paris,
            scheduled_departure=now - timezone.timedelta(hours=2),
            scheduled_arrival=now + timezone.timedelta(hours=1),
            actual_departure=now - timezone.timedelta(hours=1),
            status="delayed",
            source_type="api",
        )

        cls.flight_cancelled = Flight.objects.create(
            flight_number="AN106",
            airline=cls.airline_beta,
            aircraft=None,
            origin_airport=cls.paris,
            destination_airport=cls.berlin,
            scheduled_departure=now + timezone.timedelta(hours=3),
            scheduled_arrival=now + timezone.timedelta(hours=5),
            status="cancelled",
            source_type="local",
        )


class AnalyticsHelperTests(TestCase):
    def test_status_label_returns_known_and_unknown_labels(self):
        self.assertEqual(str(views._status_label("scheduled")), "Scheduled")
        self.assertEqual(str(views._status_label("boarding")), "Boarding")
        self.assertEqual(str(views._status_label("departed")), "Departed")
        self.assertEqual(str(views._status_label("in_air")), "In Air")
        self.assertEqual(str(views._status_label("landed")), "Landed")
        self.assertEqual(str(views._status_label("delayed")), "Delayed")
        self.assertEqual(str(views._status_label("cancelled")), "Cancelled")
        self.assertEqual(str(views._status_label("unknown")), "Unknown")

    def test_source_label_returns_known_and_unknown_labels(self):
        self.assertEqual(str(views._source_label("api")), "API synchronized")
        self.assertEqual(str(views._source_label("local")), "Local records")
        self.assertEqual(str(views._source_label("external")), "Unspecified source")

    def test_safe_rate_handles_zero_and_normal_values(self):
        self.assertEqual(views._safe_rate(0, 0), 0)
        self.assertEqual(views._safe_rate(2, 4), 50.0)
        self.assertEqual(views._safe_rate(1, 3), 33.3)

    def test_combine_q_returns_empty_query_when_no_expressions(self):
        query = views._combine_q([])

        self.assertEqual(str(query), "(AND: ('pk__in', []))")


class AnalyticsContextBusinessTests(AnalyticsTestDataMixin, TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_selected_airline_id_handles_all_empty_invalid_and_valid_values(self):
        request_all = self.factory.get("/analytics/", {"airline": "all"})
        request_empty = self.factory.get("/analytics/", {"airline": ""})
        request_invalid = self.factory.get("/analytics/", {"airline": "abc"})
        request_valid = self.factory.get("/analytics/", {"airline": str(self.airline_alpha.id)})

        self.assertIsNone(views._get_selected_airline_id(request_all))
        self.assertIsNone(views._get_selected_airline_id(request_empty))
        self.assertIsNone(views._get_selected_airline_id(request_invalid))
        self.assertEqual(views._get_selected_airline_id(request_valid), self.airline_alpha.id)

    def test_base_context_without_filters_builds_operational_intelligence_metrics(self):
        request = self.factory.get("/analytics/")
        context = views._build_intelligence_context(request, active_page="overview")

        self.assertEqual(context["active_page"], "overview")
        self.assertEqual(context["base_total_flights"], 7)
        self.assertEqual(context["total_flights"], 7)

        self.assertEqual(context["scheduled_count"], 1)
        self.assertEqual(context["delayed_count"], 1)
        self.assertEqual(context["cancelled_count"], 1)
        self.assertEqual(context["active_count"], 3)
        self.assertEqual(context["landed_count"], 1)

        self.assertEqual(context["api_count"], 3)
        self.assertEqual(context["local_count"], 4)
        self.assertEqual(context["unknown_source_count"], 0)

        self.assertEqual(context["critical_count"], 1)
        self.assertEqual(context["attention_count"], 1)
        self.assertEqual(context["irregular_ops_count"], 2)
        self.assertEqual(context["stable_count"], 5)

        self.assertEqual(context["delay_rate"], 14.3)
        self.assertEqual(context["cancellation_rate"], 14.3)
        self.assertEqual(context["active_rate"], 42.9)
        self.assertEqual(context["critical_rate"], 14.3)
        self.assertEqual(context["attention_rate"], 14.3)

        self.assertIn(context["monitoring_mode"], ["Critical Supervision", "Elevated Supervision", "Stable Operations"])
        self.assertIn(context["supervision_class"], ["critical", "elevated", "stable"])
        self.assertGreaterEqual(len(context["recommendations"]), 1)

        self.assertEqual(len(context["status_rows"]), 7)
        self.assertEqual(len(context["status_labels"]), 7)
        self.assertEqual(len(context["status_values"]), 7)

        self.assertGreaterEqual(len(context["top_airlines"]), 1)
        self.assertGreaterEqual(len(context["top_routes"]), 1)
        self.assertGreaterEqual(len(context["top_origin_airports"]), 1)
        self.assertGreaterEqual(len(context["top_destination_airports"]), 1)

        self.assertEqual(len(context["source_labels"]), 3)
        self.assertEqual(len(context["source_values"]), 3)

        self.assertEqual(len(context["disruption_mix_labels"]), 3)
        self.assertEqual(len(context["disruption_mix_values"]), 3)

        self.assertEqual(len(context["legacy_disruption_mix_labels"]), 3)
        self.assertEqual(len(context["legacy_disruption_mix_values"]), 3)

        self.assertGreaterEqual(len(context["airline_filter_options"]), 2)
        self.assertFalse(context["is_filtered"])

    def test_context_filters_by_status(self):
        request = self.factory.get("/analytics/", {"status": "delayed"})
        context = views._build_intelligence_context(request, active_page="reports")

        self.assertEqual(context["active_page"], "reports")
        self.assertEqual(context["selected_status"], "delayed")
        self.assertEqual(context["selected_source"], "all")
        self.assertEqual(context["total_flights"], 1)
        self.assertEqual(context["delayed_count"], 1)
        self.assertTrue(context["is_filtered"])

    def test_context_filters_by_source(self):
        request = self.factory.get("/analytics/", {"source": "api"})
        context = views._build_intelligence_context(request, active_page="charts")

        self.assertEqual(context["active_page"], "charts")
        self.assertEqual(context["selected_source"], "api")
        self.assertEqual(context["total_flights"], 3)
        self.assertEqual(context["api_count"], 3)
        self.assertEqual(context["local_count"], 0)
        self.assertTrue(context["is_filtered"])

    def test_context_filters_by_airline(self):
        request = self.factory.get(
            "/analytics/",
            {
                "airline": str(self.airline_alpha.id),
            },
        )
        context = views._build_intelligence_context(request, active_page="routes")

        self.assertEqual(context["active_page"], "routes")
        self.assertEqual(context["selected_airline_id"], self.airline_alpha.id)
        self.assertEqual(context["total_flights"], 4)
        self.assertEqual(context["most_active_airline"], "Alpha Airways")
        self.assertTrue(context["is_filtered"])

    def test_invalid_filters_are_normalized_to_all(self):
        request = self.factory.get(
            "/analytics/",
            {
                "status": "wrong-status",
                "source": "wrong-source",
                "airline": "not-a-number",
            },
        )
        context = views._build_intelligence_context(request, active_page="overview")

        self.assertEqual(context["selected_status"], "all")
        self.assertEqual(context["selected_source"], "all")
        self.assertIsNone(context["selected_airline_id"])
        self.assertEqual(context["total_flights"], 7)
        self.assertFalse(context["is_filtered"])

    def test_empty_dataset_context_is_safe(self):
        Flight.objects.all().delete()

        request = self.factory.get("/analytics/")
        context = views._build_intelligence_context(request, active_page="overview")

        self.assertEqual(context["total_flights"], 0)
        self.assertEqual(context["performance_score"], 0)
        self.assertEqual(str(context["dominant_status"]), "No data")
        self.assertEqual(str(context["most_active_airline"]), "No data")
        self.assertEqual(str(context["busiest_route"]), "No data")
        self.assertGreaterEqual(len(context["recommendations"]), 1)


class AnalyticsViewRenderTests(AnalyticsTestDataMixin, TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _assert_view_uses_template_and_active_page(self, view_function, path, template_name, active_page):
        request = self.factory.get(path)

        with self.settings(ROOT_URLCONF="config.urls"):
            with self.assertTemplateNotUsed("template-that-should-not-exist.html"):
                pass

        from unittest.mock import patch
        from types import SimpleNamespace

        with patch("apps.analytics.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = view_function(request)

            self.assertEqual(response.status_code, 200)

            used_template = mocked_render.call_args.args[1]
            context = mocked_render.call_args.args[2]

            self.assertEqual(used_template, template_name)
            self.assertEqual(context["active_page"], active_page)
            self.assertIn("total_flights", context)
            self.assertIn("recommendations", context)

    def test_analytics_home_view(self):
        self._assert_view_uses_template_and_active_page(
            views.analytics_home,
            "/analytics/",
            "analytics/index.html",
            "overview",
        )

    def test_analytics_reports_view(self):
        self._assert_view_uses_template_and_active_page(
            views.analytics_reports,
            "/analytics/reports/",
            "analytics/reports.html",
            "reports",
        )

    def test_analytics_charts_view(self):
        self._assert_view_uses_template_and_active_page(
            views.analytics_charts,
            "/analytics/charts/",
            "analytics/charts.html",
            "charts",
        )

    def test_analytics_routes_view(self):
        self._assert_view_uses_template_and_active_page(
            views.analytics_routes,
            "/analytics/routes/",
            "analytics/routes.html",
            "routes",
        )

    def test_analytics_reliability_view(self):
        self._assert_view_uses_template_and_active_page(
            views.analytics_reliability,
            "/analytics/reliability/",
            "analytics/reliability.html",
            "reliability",
        )

    def test_analytics_feedback_view(self):
        self._assert_view_uses_template_and_active_page(
            views.analytics_feedback,
            "/analytics/feedback/",
            "analytics/feedback.html",
            "feedback",
        )