from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.airlines.models import Airline
from apps.airports import views
from apps.airports.models import Airport
from apps.flights.models import Flight


class AirportViewsTestDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.airline = Airline.objects.create(
            name="Airport Test Airways",
            iata_code="AT",
            icao_code="ATA",
            country="Belarus",
        )

        cls.complete_airport = Airport.objects.create(
            name="Airport Complete Hub",
            iata_code="ACH",
            icao_code="UACH",
            city="Minsk",
            country="Belarus",
            latitude=53.882500,
            longitude=28.030700,
            is_active=True,
        )

        cls.partial_airport = Airport.objects.create(
            name="Airport Partial Hub",
            iata_code="APH",
            icao_code="UAPH",
            city="Paris",
            country="",
            latitude=49.009700,
            longitude=None,
            is_active=True,
        )

        cls.minimal_airport = Airport.objects.create(
            name="Airport Minimal Hub",
            iata_code="AMH",
            icao_code="UAMH",
            city="",
            country="",
            latitude=None,
            longitude=None,
            is_active=False,
        )

        now = timezone.now()

        cls.departure_flight = Flight.objects.create(
            flight_number="AP100",
            airline=cls.airline,
            aircraft=None,
            origin_airport=cls.complete_airport,
            destination_airport=cls.partial_airport,
            scheduled_departure=now + timezone.timedelta(hours=2),
            scheduled_arrival=now + timezone.timedelta(hours=4),
            status="scheduled",
            source_type="local",
        )

        cls.arrival_flight = Flight.objects.create(
            flight_number="AP101",
            airline=cls.airline,
            aircraft=None,
            origin_airport=cls.partial_airport,
            destination_airport=cls.complete_airport,
            scheduled_departure=now + timezone.timedelta(hours=3),
            scheduled_arrival=now + timezone.timedelta(hours=5),
            status="in_air",
            source_type="api",
        )

        cls.disrupted_flight = Flight.objects.create(
            flight_number="AP102",
            airline=cls.airline,
            aircraft=None,
            origin_airport=cls.complete_airport,
            destination_airport=cls.minimal_airport,
            scheduled_departure=now + timezone.timedelta(hours=6),
            scheduled_arrival=now + timezone.timedelta(hours=8),
            status="delayed",
            source_type="api",
        )

        cls.cancelled_flight = Flight.objects.create(
            flight_number="AP103",
            airline=cls.airline,
            aircraft=None,
            origin_airport=cls.minimal_airport,
            destination_airport=cls.complete_airport,
            scheduled_departure=now + timezone.timedelta(hours=9),
            scheduled_arrival=now + timezone.timedelta(hours=11),
            status="cancelled",
            source_type="local",
        )


class AirportHelperTests(TestCase):
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
        self.assertTrue(views.is_meaningful_text("Minsk"))
        self.assertTrue(views.is_meaningful_text(" Belarus "))


class AirportCompletenessTests(AirportViewsTestDataMixin, TestCase):
    def test_complete_airport_has_complete_quality_level(self):
        completeness = views.get_airport_data_completeness(self.complete_airport)

        self.assertEqual(completeness["filled_fields"], 4)
        self.assertEqual(completeness["total_fields"], 4)
        self.assertEqual(completeness["score"], 100)
        self.assertEqual(completeness["level"], "complete")
        self.assertEqual(completeness["label"], "Complete")
        self.assertEqual(completeness["missing_fields"], [])
        self.assertTrue(completeness["is_complete"])
        self.assertTrue(completeness["has_coordinates"])

    def test_partial_airport_has_partial_quality_level(self):
        completeness = views.get_airport_data_completeness(self.partial_airport)

        self.assertEqual(completeness["filled_fields"], 2)
        self.assertEqual(completeness["score"], 50)
        self.assertEqual(completeness["level"], "partial")
        self.assertEqual(completeness["label"], "Partial")
        self.assertIn("country", completeness["missing_fields"])
        self.assertIn("longitude", completeness["missing_fields"])
        self.assertFalse(completeness["is_complete"])
        self.assertFalse(completeness["has_coordinates"])

    def test_minimal_airport_has_minimal_quality_level(self):
        completeness = views.get_airport_data_completeness(self.minimal_airport)

        self.assertEqual(completeness["filled_fields"], 0)
        self.assertEqual(completeness["score"], 0)
        self.assertEqual(completeness["level"], "minimal")
        self.assertEqual(completeness["label"], "Minimal")
        self.assertFalse(completeness["is_complete"])
        self.assertFalse(completeness["has_coordinates"])

    def test_quality_distribution_groups_airports_by_completeness_level(self):
        distribution = views.get_airport_quality_distribution(
            Airport.objects.order_by("name")
        )

        self.assertEqual(distribution["complete_airports"], 1)
        self.assertEqual(distribution["partial_airports"], 1)
        self.assertEqual(distribution["minimal_airports"], 1)


class AirportListViewTests(AirportViewsTestDataMixin, TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_airport_list_builds_registry_quality_context(self):
        request = self.factory.get("/airports/")

        with patch("apps.airports.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.airport_list(request)

        self.assertEqual(response.status_code, 200)

        template_name = mocked_render.call_args.args[1]
        context = mocked_render.call_args.args[2]

        self.assertEqual(template_name, "airports/list.html")
        self.assertEqual(context["total_airports"], 3)
        self.assertEqual(context["total_active_airports"], 2)
        self.assertEqual(context["total_countries"], 1)
        self.assertEqual(context["complete_airports"], 1)
        self.assertEqual(context["partial_airports"], 1)
        self.assertEqual(context["minimal_airports"], 1)
        self.assertEqual(context["query"], "")
        self.assertEqual(len(context["airports"]), 3)

        first_airport = context["airports"][0]

        self.assertTrue(hasattr(first_airport, "flight_count"))
        self.assertTrue(hasattr(first_airport, "data_completeness"))
        self.assertTrue(hasattr(first_airport, "data_quality_level"))
        self.assertTrue(hasattr(first_airport, "data_quality_label"))
        self.assertTrue(hasattr(first_airport, "data_quality_score"))
        self.assertTrue(hasattr(first_airport, "missing_data_fields"))
        self.assertTrue(hasattr(first_airport, "has_coordinates"))

    def test_airport_list_filters_by_query(self):
        request = self.factory.get("/airports/", {"q": "Partial"})

        with patch("apps.airports.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.airport_list(request)

        self.assertEqual(response.status_code, 200)

        context = mocked_render.call_args.args[2]

        self.assertEqual(context["query"], "Partial")
        self.assertEqual(len(context["airports"]), 1)
        self.assertEqual(context["airports"][0].iata_code, "APH")

    def test_airport_list_searches_by_country_city_and_codes(self):
        request = self.factory.get("/airports/", {"q": "ACH"})

        with patch("apps.airports.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.airport_list(request)

        self.assertEqual(response.status_code, 200)

        context = mocked_render.call_args.args[2]

        self.assertEqual(len(context["airports"]), 1)
        self.assertEqual(context["airports"][0].iata_code, "ACH")


class AirportDetailViewTests(AirportViewsTestDataMixin, TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_airport_detail_builds_flight_activity_context(self):
        request = self.factory.get(f"/airports/{self.complete_airport.pk}/")

        with patch("apps.airports.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.airport_detail(request, self.complete_airport.pk)

        self.assertEqual(response.status_code, 200)

        template_name = mocked_render.call_args.args[1]
        context = mocked_render.call_args.args[2]

        self.assertEqual(template_name, "airports/detail.html")
        self.assertEqual(context["airport"].iata_code, "ACH")
        self.assertEqual(context["total_flights"], 4)
        self.assertEqual(context["departure_count"], 2)
        self.assertEqual(context["arrival_count"], 2)
        self.assertEqual(context["active_flights"], 3)
        self.assertEqual(context["disrupted_flights"], 2)
        self.assertLessEqual(len(context["recent_flights"]), 10)
        self.assertEqual(context["data_quality_level"], "complete")
        self.assertEqual(context["data_quality_label"], "Complete")
        self.assertEqual(context["data_quality_score"], 100)
        self.assertTrue(context["has_coordinates"])

    def test_airport_detail_builds_context_for_minimal_airport(self):
        request = self.factory.get(f"/airports/{self.minimal_airport.pk}/")

        with patch("apps.airports.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.airport_detail(request, self.minimal_airport.pk)

        self.assertEqual(response.status_code, 200)

        context = mocked_render.call_args.args[2]

        self.assertEqual(context["airport"].iata_code, "AMH")
        self.assertEqual(context["data_quality_level"], "minimal")
        self.assertFalse(context["has_coordinates"])
        self.assertIn("city", context["missing_data_fields"])

    def test_airport_detail_raises_404_for_unknown_airport(self):
        request = self.factory.get("/airports/999999/")

        with self.assertRaises(Exception):
            views.airport_detail(request, 999999)