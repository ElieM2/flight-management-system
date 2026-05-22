from datetime import timedelta
import random

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.aircraft.models import Aircraft
from apps.airlines.models import Airline
from apps.airports.models import Airport
from apps.flights.models import Flight, FlightStatusHistory


class Command(BaseCommand):
    help = "Seed demo operational data for AirMonitor"

    def handle(self, *args, **options):
        random.seed(42)
        now = timezone.now()

        self.stdout.write(self.style.WARNING("Seeding AirMonitor demo data..."))

        airlines_data = [
            {"name": "Air France", "iata_code": "AF", "icao_code": "AFR", "country": "France"},
            {"name": "Lufthansa", "iata_code": "LH", "icao_code": "DLH", "country": "Germany"},
            {"name": "Turkish Airlines", "iata_code": "TK", "icao_code": "THY", "country": "Turkey"},
            {"name": "Qatar Airways", "iata_code": "QR", "icao_code": "QTR", "country": "Qatar"},
            {"name": "LOT Polish Airlines", "iata_code": "LO", "icao_code": "LOT", "country": "Poland"},
        ]

        airports_data = [
            {
                "name": "Paris Charles de Gaulle Airport",
                "iata_code": "CDG",
                "icao_code": "LFPG",
                "city": "Paris",
                "country": "France",
                "latitude": 49.009700,
                "longitude": 2.547900,
            },
            {
                "name": "Frankfurt Airport",
                "iata_code": "FRA",
                "icao_code": "EDDF",
                "city": "Frankfurt",
                "country": "Germany",
                "latitude": 50.037900,
                "longitude": 8.562200,
            },
            {
                "name": "Istanbul Airport",
                "iata_code": "IST",
                "icao_code": "LTFM",
                "city": "Istanbul",
                "country": "Turkey",
                "latitude": 41.275300,
                "longitude": 28.751900,
            },
            {
                "name": "Warsaw Chopin Airport",
                "iata_code": "WAW",
                "icao_code": "EPWA",
                "city": "Warsaw",
                "country": "Poland",
                "latitude": 52.165700,
                "longitude": 20.967100,
            },
            {
                "name": "Hamad International Airport",
                "iata_code": "DOH",
                "icao_code": "OTHH",
                "city": "Doha",
                "country": "Qatar",
                "latitude": 25.273100,
                "longitude": 51.608100,
            },
            {
                "name": "Minsk National Airport",
                "iata_code": "MSQ",
                "icao_code": "UMMS",
                "city": "Minsk",
                "country": "Belarus",
                "latitude": 53.882500,
                "longitude": 28.030700,
            },
        ]

        aircraft_models = [
            ("Airbus A320", "A320", 180),
            ("Airbus A321", "A321", 210),
            ("Boeing 737-800", "B738", 189),
            ("Boeing 787-8", "B788", 242),
            ("Airbus A330-300", "A333", 290),
        ]

        airlines = {}
        for item in airlines_data:
            airline, _ = Airline.objects.update_or_create(
                iata_code=item["iata_code"],
                defaults=item,
            )
            airlines[item["iata_code"]] = airline

        airports = {}
        for item in airports_data:
            airport, _ = Airport.objects.update_or_create(
                iata_code=item["iata_code"],
                defaults=item,
            )
            airports[item["iata_code"]] = airport

        aircraft_registry = {}
        reg_counter = 1
        for airline_code, airline in airlines.items():
            for model_name, aircraft_type, capacity in aircraft_models[:2]:
                registration = f"{airline_code}-DM{reg_counter:03d}"
                aircraft, _ = Aircraft.objects.update_or_create(
                    registration_number=registration,
                    defaults={
                        "airline": airline,
                        "model": model_name,
                        "aircraft_type": aircraft_type,
                        "capacity": capacity,
                        "status": "active",
                    },
                )
                aircraft_registry.setdefault(airline_code, []).append(aircraft)
                reg_counter += 1

        routes = [
            ("AF", "CDG", "FRA"),
            ("AF", "CDG", "IST"),
            ("LH", "FRA", "WAW"),
            ("LH", "FRA", "MSQ"),
            ("TK", "IST", "CDG"),
            ("TK", "IST", "DOH"),
            ("QR", "DOH", "IST"),
            ("QR", "DOH", "CDG"),
            ("LO", "WAW", "FRA"),
            ("LO", "WAW", "MSQ"),
        ]

        flight_specs = [
            {"status": "scheduled", "source_type": "local"},
            {"status": "boarding", "source_type": "local"},
            {"status": "departed", "source_type": "api"},
            {"status": "in_air", "source_type": "api"},
            {"status": "landed", "source_type": "local"},
            {"status": "delayed", "source_type": "api"},
            {"status": "cancelled", "source_type": "local"},
            {"status": "in_air", "source_type": "api"},
            {"status": "boarding", "source_type": "api"},
            {"status": "delayed", "source_type": "local"},
            {"status": "departed", "source_type": "api"},
            {"status": "scheduled", "source_type": "local"},
        ]

        created_flights = []

        for index, spec in enumerate(flight_specs, start=1):
            airline_code, origin_code, destination_code = routes[(index - 1) % len(routes)]
            airline = airlines[airline_code]
            origin = airports[origin_code]
            destination = airports[destination_code]
            aircraft = random.choice(aircraft_registry[airline_code])

            departure = now + timedelta(hours=(index - 5) * 2)
            arrival = departure + timedelta(hours=random.choice([2, 3, 4, 5, 6]))

            flight_number = f"{airline_code}{100 + index}"
            status = spec["status"]
            source_type = spec["source_type"]

            actual_departure = None
            actual_arrival = None
            live_latitude = None
            live_longitude = None
            live_altitude = None
            live_speed = None
            live_direction = None
            external_id = None

            if source_type == "api":
                external_id = f"EXT-{flight_number}"

            if status in ["departed", "in_air", "landed", "delayed"]:
                actual_departure = departure + timedelta(minutes=random.choice([0, 8, 12, 18, 35, 55]))

            if status == "landed":
                actual_arrival = arrival + timedelta(minutes=random.choice([0, 10, 18, 25]))

            if status == "delayed":
                if actual_departure is None:
                    actual_departure = departure + timedelta(minutes=random.choice([35, 45, 70, 95]))

            if status in ["departed", "in_air"]:
                progress = 0.35 if status == "departed" else 0.68
                origin_lat = float(origin.latitude)
                origin_lng = float(origin.longitude)
                destination_lat = float(destination.latitude)
                destination_lng = float(destination.longitude)

                live_latitude = origin_lat + ((destination_lat - origin_lat) * progress)
                live_longitude = origin_lng + ((destination_lng - origin_lng) * progress)
                live_altitude = 2800 if status == "departed" else random.choice([8800, 9600, 10200, 11000])
                live_speed = 240 if status == "departed" else random.choice([620, 690, 740, 810])
                live_direction = random.choice([45, 75, 110, 145, 190, 235, 280, 315])

            if status == "in_air" and source_type == "api":
                live_latitude = round(live_latitude, 6)
                live_longitude = round(live_longitude, 6)

            flight, _ = Flight.objects.update_or_create(
                flight_number=flight_number,
                defaults={
                    "airline": airline,
                    "aircraft": aircraft,
                    "origin_airport": origin,
                    "destination_airport": destination,
                    "scheduled_departure": departure,
                    "scheduled_arrival": arrival,
                    "actual_departure": actual_departure,
                    "actual_arrival": actual_arrival,
                    "status": status,
                    "source_type": source_type,
                    "external_id": external_id,
                    "live_latitude": live_latitude,
                    "live_longitude": live_longitude,
                    "live_altitude": live_altitude,
                    "live_speed": live_speed,
                    "live_direction": live_direction,
                },
            )
            created_flights.append(flight)

        for flight in created_flights:
            FlightStatusHistory.objects.filter(flight=flight).delete()

            FlightStatusHistory.objects.create(
                flight=flight,
                previous_status=None,
                new_status="scheduled",
                change_type="created",
                source_type_snapshot=flight.source_type,
                scheduled_departure_snapshot=flight.scheduled_departure,
                scheduled_arrival_snapshot=flight.scheduled_arrival,
                actual_departure_snapshot=None,
                actual_arrival_snapshot=None,
                departure_delay_minutes=None,
                arrival_delay_minutes=None,
                is_disruption_event=False,
                status_changed=True,
                schedule_changed=False,
                live_data_changed=False,
                change_summary="Flight record created.",
            )

            if flight.status in ["boarding", "departed", "in_air", "landed", "delayed", "cancelled"]:
                previous_status = "scheduled"
                summary_map = {
                    "boarding": "Boarding phase started.",
                    "departed": "Flight departure confirmed.",
                    "in_air": "Flight is currently airborne.",
                    "landed": "Flight landed successfully.",
                    "delayed": "Departure delay detected and recorded.",
                    "cancelled": "Flight cancellation recorded.",
                }

                FlightStatusHistory.objects.create(
                    flight=flight,
                    previous_status=previous_status,
                    new_status=flight.status,
                    change_type="status",
                    source_type_snapshot=flight.source_type,
                    scheduled_departure_snapshot=flight.scheduled_departure,
                    scheduled_arrival_snapshot=flight.scheduled_arrival,
                    actual_departure_snapshot=flight.actual_departure,
                    actual_arrival_snapshot=flight.actual_arrival,
                    departure_delay_minutes=flight.get_departure_delay_minutes(),
                    arrival_delay_minutes=flight.get_arrival_delay_minutes(),
                    is_disruption_event=flight.status in ["delayed", "cancelled"],
                    status_changed=True,
                    schedule_changed=flight.status == "delayed",
                    live_data_changed=flight.status in ["departed", "in_air"],
                    change_summary=summary_map[flight.status],
                )

            if flight.status in ["departed", "in_air"] and flight.live_latitude is not None:
                FlightStatusHistory.objects.create(
                    flight=flight,
                    previous_status=flight.status,
                    new_status=flight.status,
                    change_type="live",
                    source_type_snapshot=flight.source_type,
                    scheduled_departure_snapshot=flight.scheduled_departure,
                    scheduled_arrival_snapshot=flight.scheduled_arrival,
                    actual_departure_snapshot=flight.actual_departure,
                    actual_arrival_snapshot=flight.actual_arrival,
                    departure_delay_minutes=flight.get_departure_delay_minutes(),
                    arrival_delay_minutes=flight.get_arrival_delay_minutes(),
                    is_disruption_event=False,
                    status_changed=False,
                    schedule_changed=False,
                    live_data_changed=True,
                    change_summary="Live telemetry updated for active flight.",
                )

        self.stdout.write(self.style.SUCCESS("Demo operational data created successfully."))
        self.stdout.write(self.style.SUCCESS(f"Flights: {Flight.objects.count()}"))
        self.stdout.write(self.style.SUCCESS(f"History entries: {FlightStatusHistory.objects.count()}"))