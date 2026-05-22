from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.aircraft.models import Aircraft
from apps.airlines import views
from apps.airlines.models import Airline
from apps.airports.models import Airport
from apps.flights.models import Flight


class AirlineViewsTestDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.airline_alpha = Airline.objects.create(
            name="Airline Alpha Airways",
            iata_code="LA",
            icao_code="LAA",
            country="Belarus",
            is_active=True,
        )

        cls.airline_beta = Airline.objects.create(
            name="Airline Beta Wings",
            iata_code="LB",
            icao_code="LBB",
            country="France",
            is_active=False,
        )

        cls.airline_empty = Airline.objects.create(
            name="Airline Empty Carrier",
            iata_code="LE",
            icao_code="LEE",
            country="unknown",
            is_active=True,
        )

        cls.minsk = Airport.objects.create(
            name="Airline Minsk Airport",
            iata_code="LMS",
            icao_code="ULMS",
            city="Minsk",
            country="Belarus",
            latitude=53.882500,
            longitude=28.030700,
        )

        cls.paris = Airport.objects.create(
            name="Airline Paris Airport",
            iata_code="LPA",
            icao_code="ULPA",
            city="Paris",
            country="France",
            latitude=49.009700,
            longitude=2.547900,
        )

        cls.berlin = Airport.objects.create(
            name="Airline Berlin Airport",
            iata_code="LBE",
            icao_code="ULBE",
            city="Berlin",
            country="Germany",
            latitude=52.366700,
            longitude=13.503300,
        )

        cls.aircraft_alpha = Aircraft.objects.create(
            airline=cls.airline_alpha,
            model="Airbus A320",
            registration_number="EW-LINE-A",
            aircraft_type="A320",
            capacity=180,
            status="active",
        )

        cls.aircraft_beta = Aircraft.objects.create(
            airline=cls.airline_alpha,
            model="Boeing 737",
            registration_number="EW-LINE-B",
            aircraft_type="B737",
            capacity=160,
            status="active",
        )

        now = timezone.now()

        cls.flight_scheduled = Flight.objects.create(
            flight_number="AL100",
            airline=cls.airline_alpha,
            aircraft=cls.aircraft_alpha,
            origin_airport=cls.minsk,
            destination_airport=cls.paris,
            scheduled_departure=now + timezone.timedelta(hours=2),
            scheduled_arrival=now + timezone.timedelta(hours=5),
            status="scheduled",
            source_type="local",
        )

        cls.flight_in_air = Flight.objects.create(
            flight_number="AL101",
            airline=cls.airline_alpha,
            aircraft=cls.aircraft_beta,
            origin_airport=cls.paris,
            destination_airport=cls.minsk,
            scheduled_departure=now - timezone.timedelta(hours=1),
            scheduled_arrival=now + timezone.timedelta(hours=2),
            status="in_air",
            source_type="api",
        )

        cls.flight_delayed = Flight.objects.create(
            flight_number="AL102",
            airline=cls.airline_alpha,
            aircraft=cls.aircraft_alpha,
            origin_airport=cls.minsk,
            destination_airport=cls.berlin,
            scheduled_departure=now - timezone.timedelta(hours=2),
            scheduled_arrival=now + timezone.timedelta(hours=1),
            status="delayed",
            source_type="api",
        )

        cls.flight_cancelled = Flight.objects.create(
            flight_number="AL103",
            airline=cls.airline_alpha,
            aircraft=None,
            origin_airport=cls.berlin,
            destination_airport=cls.paris,
            scheduled_departure=now + timezone.timedelta(hours=3),
            scheduled_arrival=now + timezone.timedelta(hours=5),
            status="cancelled",
            source_type="local",
        )

        cls.flight_landed = Flight.objects.create(
            flight_number="AL104",
            airline=cls.airline_beta,
            aircraft=None,
            origin_airport=cls.paris,
            destination_airport=cls.berlin,
            scheduled_departure=now - timezone.timedelta(hours=6),
            scheduled_arrival=now - timezone.timedelta(hours=4),
            actual_arrival=now - timezone.timedelta(hours=4),
            status="landed",
            source_type="local",
        )


class AirlineHelperTests(TestCase):
    def test_is_meaningful_text_rejects_empty_and_placeholder_values(self):
        self.assertFalse(views.is_meaningful_text(None))
        self.assertFalse(views.is_meaningful_text(""))
        self.assertFalse(views.is_meaningful_text("   "))
        self.assertFalse(views.is_meaningful_text("unknown"))
        self.assertFalse(views.is_meaningful_text("N/A"))
        self.assertFalse(views.is_meaningful_text("null"))
        self.assertFalse(views.is_meaningful_text("none"))
        self.assertFalse(views.is_meaningful_text("—"))
        self.assertFalse(views.is_meaningful_text("-"))

    def test_is_meaningful_text_accepts_real_values(self):
        self.assertTrue(views.is_meaningful_text("Belarus"))
        self.assertTrue(views.is_meaningful_text(" France "))


class AirlineListViewTests(AirlineViewsTestDataMixin, TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_airline_list_builds_airline_context_without_filter(self):
        request = self.factory.get("/airlines/")

        with patch("apps.airlines.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.airline_list(request)

        self.assertEqual(response.status_code, 200)

        template_name = mocked_render.call_args.args[1]
        context = mocked_render.call_args.args[2]

        self.assertEqual(template_name, "airlines/list.html")
        self.assertEqual(context["query"], "")
        self.assertEqual(context["total_airlines"], 3)
        self.assertEqual(context["total_active_airlines"], 2)
        self.assertEqual(context["total_countries"], 2)
        self.assertEqual(context["total_flights"], 5)
        self.assertEqual(len(context["airlines"]), 3)

        airline_map = {
            airline.iata_code: airline.flight_count
            for airline in context["airlines"]
        }

        self.assertEqual(airline_map["LA"], 4)
        self.assertEqual(airline_map["LB"], 1)
        self.assertEqual(airline_map["LE"], 0)

    def test_airline_list_filters_by_name_code_and_country(self):
        queries = [
            ("Alpha", "LA"),
            ("LBB", "LB"),
            ("France", "LB"),
        ]

        for query, expected_iata in queries:
            with self.subTest(query=query):
                request = self.factory.get("/airlines/", {"q": query})

                with patch("apps.airlines.views.render") as mocked_render:
                    mocked_render.return_value = SimpleNamespace(status_code=200)

                    response = views.airline_list(request)

                self.assertEqual(response.status_code, 200)

                context = mocked_render.call_args.args[2]

                self.assertEqual(context["query"], query)
                self.assertEqual(len(context["airlines"]), 1)
                self.assertEqual(context["airlines"][0].iata_code, expected_iata)


class AirlineDetailViewTests(AirlineViewsTestDataMixin, TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _get_detail_context(self, airline):
        request = self.factory.get(f"/airlines/{airline.pk}/")

        with patch("apps.airlines.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.airline_detail(request, airline.pk)

        self.assertEqual(response.status_code, 200)

        template_name = mocked_render.call_args.args[1]
        context = mocked_render.call_args.args[2]

        self.assertEqual(template_name, "airlines/detail.html")

        return context

    def test_airline_detail_builds_active_disrupted_context(self):
        context = self._get_detail_context(self.airline_alpha)

        self.assertEqual(context["airline"].iata_code, "LA")
        self.assertEqual(context["total_flights"], 4)
        self.assertEqual(context["active_flights"], 3)
        self.assertEqual(context["disrupted_flights"], 2)
        self.assertEqual(context["completed_flights"], 0)
        self.assertEqual(context["aircraft_count"], 2)
        self.assertLessEqual(len(context["recent_flights"]), 10)
        self.assertIn("active operations", context["operational_note"].lower())
        self.assertIn("disruption", context["operational_note"].lower())

    def test_airline_detail_builds_completed_operations_context(self):
        context = self._get_detail_context(self.airline_beta)

        self.assertEqual(context["airline"].iata_code, "LB")
        self.assertEqual(context["total_flights"], 1)
        self.assertEqual(context["active_flights"], 0)
        self.assertEqual(context["disrupted_flights"], 0)
        self.assertEqual(context["completed_flights"], 1)
        self.assertEqual(context["aircraft_count"], 0)
        self.assertIn("completed", context["operational_note"].lower())

    def test_airline_detail_builds_no_activity_context(self):
        context = self._get_detail_context(self.airline_empty)

        self.assertEqual(context["airline"].iata_code, "LE")
        self.assertEqual(context["total_flights"], 0)
        self.assertEqual(context["active_flights"], 0)
        self.assertEqual(context["disrupted_flights"], 0)
        self.assertEqual(context["completed_flights"], 0)
        self.assertEqual(context["aircraft_count"], 0)
        self.assertIn("no recent flight activity", context["operational_note"].lower())

    def test_airline_detail_raises_404_for_unknown_airline(self):
        request = self.factory.get("/airlines/999999/")

        with self.assertRaises(Exception):
            views.airline_detail(request, 999999)