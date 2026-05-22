from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, TestCase

from apps.aircraft import views
from apps.aircraft.models import Aircraft
from apps.airlines.models import Airline


class AircraftViewsTestDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.airline_alpha = Airline.objects.create(
            name="Aircraft Alpha Airways",
            iata_code="QA",
            icao_code="QAA",
            country="Belarus",
            is_active=True,
        )

        cls.airline_beta = Airline.objects.create(
            name="Aircraft Beta Wings",
            iata_code="QB",
            icao_code="QBB",
            country="France",
            is_active=True,
        )

        cls.aircraft_active = Aircraft.objects.create(
            airline=cls.airline_alpha,
            model="Airbus A320",
            registration_number="EW-ACTIVE",
            aircraft_type="A320",
            capacity=180,
            status="active",
        )

        cls.aircraft_maintenance = Aircraft.objects.create(
            airline=cls.airline_alpha,
            model="Boeing 737",
            registration_number="EW-MAINT",
            aircraft_type="B737",
            capacity=160,
            status="maintenance",
        )

        cls.aircraft_inactive = Aircraft.objects.create(
            airline=cls.airline_beta,
            model="Embraer E190",
            registration_number="EW-INACT",
            aircraft_type="E190",
            capacity=100,
            status="inactive",
        )


class AircraftListViewTests(AircraftViewsTestDataMixin, TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_aircraft_list_builds_fleet_context_without_filter(self):
        request = self.factory.get("/aircraft/")

        with patch("apps.aircraft.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.aircraft_list(request)

        self.assertEqual(response.status_code, 200)

        template_name = mocked_render.call_args.args[1]
        context = mocked_render.call_args.args[2]

        self.assertEqual(template_name, "aircraft/list.html")
        self.assertEqual(context["query"], "")
        self.assertEqual(context["total_aircraft"], 3)
        self.assertEqual(context["active_aircraft"], 1)
        self.assertEqual(context["total_capacity"], 440)
        self.assertEqual(context["operators_count"], 2)
        self.assertEqual(len(context["aircraft_list"]), 3)

        registrations = [
            aircraft.registration_number
            for aircraft in context["aircraft_list"]
        ]

        self.assertEqual(registrations, sorted(registrations))

    def test_aircraft_list_filters_by_registration_number(self):
        request = self.factory.get("/aircraft/", {"q": "ACTIVE"})

        with patch("apps.aircraft.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.aircraft_list(request)

        self.assertEqual(response.status_code, 200)

        context = mocked_render.call_args.args[2]

        self.assertEqual(context["query"], "ACTIVE")
        self.assertEqual(len(context["aircraft_list"]), 1)
        self.assertEqual(context["aircraft_list"][0].registration_number, "EW-ACTIVE")

    def test_aircraft_list_filters_by_model_type_and_airline(self):
        queries = [
            ("Boeing", "EW-MAINT"),
            ("B737", "EW-MAINT"),
            ("Beta Wings", "EW-INACT"),
        ]

        for query, expected_registration in queries:
            with self.subTest(query=query):
                request = self.factory.get("/aircraft/", {"q": query})

                with patch("apps.aircraft.views.render") as mocked_render:
                    mocked_render.return_value = SimpleNamespace(status_code=200)

                    response = views.aircraft_list(request)

                self.assertEqual(response.status_code, 200)

                context = mocked_render.call_args.args[2]

                self.assertEqual(context["query"], query)
                self.assertEqual(len(context["aircraft_list"]), 1)
                self.assertEqual(
                    context["aircraft_list"][0].registration_number,
                    expected_registration,
                )

    def test_aircraft_list_uses_total_aircraft_when_no_active_aircraft_exists(self):
        Aircraft.objects.update(status="maintenance")

        request = self.factory.get("/aircraft/")

        with patch("apps.aircraft.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.aircraft_list(request)

        self.assertEqual(response.status_code, 200)

        context = mocked_render.call_args.args[2]

        self.assertEqual(context["total_aircraft"], 3)
        self.assertEqual(context["active_aircraft"], 3)

    def test_aircraft_list_handles_empty_fleet(self):
        Aircraft.objects.all().delete()

        request = self.factory.get("/aircraft/")

        with patch("apps.aircraft.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.aircraft_list(request)

        self.assertEqual(response.status_code, 200)

        context = mocked_render.call_args.args[2]

        self.assertEqual(context["total_aircraft"], 0)
        self.assertEqual(context["active_aircraft"], 0)
        self.assertEqual(context["total_capacity"], 0)
        self.assertEqual(context["operators_count"], 0)
        self.assertEqual(len(context["aircraft_list"]), 0)