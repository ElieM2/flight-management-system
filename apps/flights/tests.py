from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.aircraft.models import Aircraft
from apps.airlines.models import Airline
from apps.airports.models import Airport
from apps.flights.models import Flight
from apps.flights import views


class FlightViewsTestDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.airline_alpha = Airline.objects.create(
            name="Flight Alpha Airways",
            iata_code="FA",
            icao_code="FAA",
            country="Belarus",
        )

        cls.airline_beta = Airline.objects.create(
            name="Flight Beta Wings",
            iata_code="FB",
            icao_code="FBB",
            country="France",
        )

        cls.minsk = Airport.objects.create(
            name="Flight Minsk National Airport",
            iata_code="FMS",
            icao_code="UFMS",
            city="Minsk",
            country="Belarus",
            latitude=53.882500,
            longitude=28.030700,
        )

        cls.paris = Airport.objects.create(
            name="Flight Paris Charles de Gaulle",
            iata_code="FCD",
            icao_code="LFCD",
            city="Paris",
            country="France",
            latitude=49.009700,
            longitude=2.547900,
        )

        cls.berlin = Airport.objects.create(
            name="Flight Berlin Brandenburg",
            iata_code="FBR",
            icao_code="EFBR",
            city="Berlin",
            country="Germany",
            latitude=52.366700,
            longitude=13.503300,
        )

        cls.aircraft = Aircraft.objects.create(
            airline=cls.airline_alpha,
            model="Airbus A320",
            registration_number="EW-FLIGHT",
            aircraft_type="A320",
            capacity=180,
            status="active",
        )

        now = timezone.now()

        cls.flight_scheduled = Flight.objects.create(
            flight_number="FL100",
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
            flight_number="FL101",
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
            flight_number="FL102",
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
            flight_number="FL103",
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
            flight_number="FL104",
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
            flight_number="FL105",
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
            flight_number="FL106",
            airline=cls.airline_beta,
            aircraft=None,
            origin_airport=cls.paris,
            destination_airport=cls.berlin,
            scheduled_departure=now + timezone.timedelta(hours=3),
            scheduled_arrival=now + timezone.timedelta(hours=5),
            status="cancelled",
            source_type="local",
        )


class FlightListViewTests(FlightViewsTestDataMixin, TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_safe_rate_handles_zero_and_regular_values(self):
        self.assertEqual(views._safe_rate(0, 0), 0)
        self.assertEqual(views._safe_rate(2, 4), 50.0)
        self.assertEqual(views._safe_rate(1, 3), 33.3)

    def test_flight_list_without_filters_builds_business_context(self):
        request = self.factory.get("/flights/")

        with patch("apps.flights.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.flight_list(request)

        self.assertEqual(response.status_code, 200)

        template_name = mocked_render.call_args.args[1]
        context = mocked_render.call_args.args[2]

        self.assertEqual(template_name, "flights/list.html")
        self.assertEqual(context["total_flights"], 7)
        self.assertEqual(context["visible_flights_count"], 7)
        self.assertEqual(context["active_flights_count"], 3)
        self.assertEqual(context["delayed_count"], 1)
        self.assertEqual(context["cancelled_count"], 1)
        self.assertEqual(context["landed_count"], 1)
        self.assertEqual(context["api_count"], 3)
        self.assertEqual(context["local_count"], 4)
        self.assertEqual(context["disruption_count"], 2)
        self.assertEqual(context["disruption_rate"], 28.6)
        self.assertEqual(context["api_rate"], 42.9)
        self.assertEqual(context["query"], "")
        self.assertEqual(context["selected_source_type"], "")
        self.assertEqual(context["selected_status"], "")
        self.assertIn("delayed", context["status_map"])
        self.assertEqual(len(context["flights"]), 7)

    def test_flight_list_filters_by_query_source_and_status(self):
        request = self.factory.get(
            "/flights/",
            {
                "q": "Alpha",
                "source_type": "api",
                "status": "delayed",
            },
        )

        with patch("apps.flights.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.flight_list(request)

        self.assertEqual(response.status_code, 200)

        context = mocked_render.call_args.args[2]

        self.assertEqual(context["query"], "Alpha")
        self.assertEqual(context["selected_source_type"], "api")
        self.assertEqual(context["selected_status"], "delayed")
        self.assertEqual(context["visible_flights_count"], 1)
        self.assertEqual(context["delayed_count"], 1)
        self.assertEqual(context["api_count"], 1)
        self.assertEqual(context["local_count"], 0)
        self.assertEqual(context["disruption_count"], 1)
        self.assertEqual(context["disruption_rate"], 100.0)
        self.assertEqual(context["api_rate"], 100.0)
        self.assertEqual(context["flights"][0].flight_number, "FL105")

    def test_flight_list_ignores_invalid_source_and_status_filters(self):
        request = self.factory.get(
            "/flights/",
            {
                "source_type": "external",
                "status": "unknown_status",
            },
        )

        with patch("apps.flights.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.flight_list(request)

        self.assertEqual(response.status_code, 200)

        context = mocked_render.call_args.args[2]

        self.assertEqual(context["selected_source_type"], "")
        self.assertEqual(context["selected_status"], "")
        self.assertEqual(context["visible_flights_count"], 7)

    def test_flight_list_supports_search_by_airport_city_and_code(self):
        request = self.factory.get("/flights/", {"q": "Berlin"})

        with patch("apps.flights.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.flight_list(request)

        self.assertEqual(response.status_code, 200)

        context = mocked_render.call_args.args[2]

        self.assertGreaterEqual(context["visible_flights_count"], 1)
        self.assertTrue(
            any(
                flight.origin_airport.city == "Berlin"
                or flight.destination_airport.city == "Berlin"
                for flight in context["flights"]
            )
        )

    def test_flight_list_paginates_visible_flights(self):
        now = timezone.now()

        for index in range(25):
            Flight.objects.create(
                flight_number=f"FLX{index:03d}",
                airline=self.airline_alpha,
                aircraft=self.aircraft,
                origin_airport=self.minsk,
                destination_airport=self.paris,
                scheduled_departure=now + timezone.timedelta(hours=index),
                scheduled_arrival=now + timezone.timedelta(hours=index + 2),
                status="scheduled",
                source_type="local",
            )

        request = self.factory.get("/flights/", {"page": "2"})

        with patch("apps.flights.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.flight_list(request)

        self.assertEqual(response.status_code, 200)

        context = mocked_render.call_args.args[2]

        self.assertEqual(context["page_obj"].number, 2)
        self.assertLessEqual(len(context["flights"]), 20)
        self.assertEqual(context["visible_flights_count"], 32)


class FlightDetailViewTests(FlightViewsTestDataMixin, TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _get_detail_context(self, flight):
        request = self.factory.get(f"/flights/{flight.pk}/")

        with patch("apps.flights.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.flight_detail(request, flight.pk)

        self.assertEqual(response.status_code, 200)

        template_name = mocked_render.call_args.args[1]
        context = mocked_render.call_args.args[2]

        self.assertEqual(template_name, "flights/detail.html")

        return context

    def test_flight_detail_builds_context_for_cancelled_flight(self):
        context = self._get_detail_context(self.flight_cancelled)

        self.assertEqual(context["flight"].flight_number, "FL106")
        self.assertIn("cancelled", context["current_operational_note"].lower())
        self.assertIn("history_entries", context)
        self.assertIn("latest_history", context)
        self.assertIn("departure_delay_minutes", context)
        self.assertIn("arrival_delay_minutes", context)
        self.assertIn("disruption_events", context)
        self.assertIn("schedule_change_events", context)
        self.assertIn("live_update_events", context)
        self.assertIn("status_change_events", context)

    def test_flight_detail_builds_context_for_delayed_flight(self):
        context = self._get_detail_context(self.flight_delayed)

        self.assertEqual(context["flight"].flight_number, "FL105")
        self.assertIn("delayed", context["current_operational_note"].lower())

    def test_flight_detail_builds_context_for_in_air_flight(self):
        context = self._get_detail_context(self.flight_in_air)

        self.assertEqual(context["flight"].flight_number, "FL103")
        self.assertIn("airborne", context["current_operational_note"].lower())

    def test_flight_detail_builds_context_for_boarding_flight(self):
        context = self._get_detail_context(self.flight_boarding)

        self.assertEqual(context["flight"].flight_number, "FL101")
        self.assertIn("boarding", context["current_operational_note"].lower())

    def test_flight_detail_builds_context_for_departed_flight(self):
        context = self._get_detail_context(self.flight_departed)

        self.assertEqual(context["flight"].flight_number, "FL102")
        self.assertIn("departed", context["current_operational_note"].lower())

    def test_flight_detail_builds_context_for_landed_flight(self):
        context = self._get_detail_context(self.flight_landed)

        self.assertEqual(context["flight"].flight_number, "FL104")
        self.assertIn("landed", context["current_operational_note"].lower())

    def test_flight_detail_builds_context_for_scheduled_flight(self):
        context = self._get_detail_context(self.flight_scheduled)

        self.assertEqual(context["flight"].flight_number, "FL100")
        self.assertIn("scheduled", context["current_operational_note"].lower())

    def test_flight_detail_raises_404_for_unknown_flight(self):
        request = self.factory.get("/flights/999999/")

        with self.assertRaises(Exception):
            views.flight_detail(request, 999999)