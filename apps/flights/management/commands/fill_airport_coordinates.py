from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.airports.models import Airport


AIRPORT_COORDINATES = {
    # Indonesia
    "CGK": {
        "latitude": "-6.125567",
        "longitude": "106.655897",
        "name": "Soekarno-Hatta International Airport",
        "city": "Jakarta",
        "country": "Indonesia",
    },
    "YIA": {
        "latitude": "-7.905338",
        "longitude": "110.057264",
        "name": "Yogyakarta International Airport",
        "city": "Yogyakarta",
        "country": "Indonesia",
    },

    # South Korea / Mongolia
    "ICN": {
        "latitude": "37.460190",
        "longitude": "126.440696",
        "name": "Incheon International Airport",
        "city": "Seoul",
        "country": "South Korea",
    },
    "UBN": {
        "latitude": "47.646916",
        "longitude": "106.819833",
        "name": "Chinggis Khaan International Airport",
        "city": "Ulaanbaatar",
        "country": "Mongolia",
    },

    # Singapore / Cambodia
    "SIN": {
        "latitude": "1.364420",
        "longitude": "103.991531",
        "name": "Singapore Changi Airport",
        "city": "Singapore",
        "country": "Singapore",
    },
    "SAI": {
        "latitude": "13.369167",
        "longitude": "104.223056",
        "name": "Siem Reap Angkor International Airport",
        "city": "Siem Reap",
        "country": "Cambodia",
    },

    # Malaysia / Indonesia
    "KUL": {
        "latitude": "2.745578",
        "longitude": "101.709917",
        "name": "Kuala Lumpur International Airport",
        "city": "Kuala Lumpur",
        "country": "Malaysia",
    },
    "DPS": {
        "latitude": "-8.748169",
        "longitude": "115.167172",
        "name": "Ngurah Rai International Airport",
        "city": "Denpasar",
        "country": "Indonesia",
    },

    # Europe / CIS examples
    "CDG": {
        "latitude": "49.009690",
        "longitude": "2.547925",
        "name": "Charles de Gaulle Airport",
        "city": "Paris",
        "country": "France",
    },
    "IST": {
        "latitude": "41.275278",
        "longitude": "28.751944",
        "name": "Istanbul Airport",
        "city": "Istanbul",
        "country": "Turkey",
    },
    "WAW": {
        "latitude": "52.165750",
        "longitude": "20.967122",
        "name": "Warsaw Chopin Airport",
        "city": "Warsaw",
        "country": "Poland",
    },
    "MSQ": {
        "latitude": "53.882469",
        "longitude": "28.030731",
        "name": "Minsk National Airport",
        "city": "Minsk",
        "country": "Belarus",
    },

    # Middle East
    "DOH": {
        "latitude": "25.273056",
        "longitude": "51.608056",
        "name": "Hamad International Airport",
        "city": "Doha",
        "country": "Qatar",
    },

    # Common airports already used in your project examples
    "JFK": {
        "latitude": "40.641311",
        "longitude": "-73.778139",
        "name": "John F. Kennedy International Airport",
        "city": "New York",
        "country": "United States",
    },
    "ORD": {
        "latitude": "41.974162",
        "longitude": "-87.907321",
        "name": "O'Hare International Airport",
        "city": "Chicago",
        "country": "United States",
    },
    "LHR": {
        "latitude": "51.470020",
        "longitude": "-0.454295",
        "name": "Heathrow Airport",
        "city": "London",
        "country": "United Kingdom",
    },
    "DXB": {
        "latitude": "25.253174",
        "longitude": "55.365673",
        "name": "Dubai International Airport",
        "city": "Dubai",
        "country": "United Arab Emirates",
    },
    "FRA": {
        "latitude": "50.037933",
        "longitude": "8.562152",
        "name": "Frankfurt Airport",
        "city": "Frankfurt",
        "country": "Germany",
    },
}


def is_missing_or_invalid_coordinate(latitude, longitude):
    if latitude is None or longitude is None:
        return True

    try:
        lat = Decimal(str(latitude))
        lng = Decimal(str(longitude))
    except Exception:
        return True

    if lat == Decimal("0") and lng == Decimal("0"):
        return True

    return False


class Command(BaseCommand):
    help = "Fill missing or invalid airport coordinates using a verified local airport coordinate dictionary."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without saving changes.",
        )

        parser.add_argument(
            "--force",
            action="store_true",
            help="Update coordinates even if airport already has non-zero coordinates.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]

        updated = 0
        skipped = 0
        not_found = 0

        self.stdout.write("")
        self.stdout.write("Filling airport coordinates...")
        self.stdout.write("-" * 70)

        with transaction.atomic():
            for iata_code, data in AIRPORT_COORDINATES.items():
                airport = Airport.objects.filter(iata_code__iexact=iata_code).first()

                if not airport:
                    not_found += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"Not found: {iata_code}"
                        )
                    )
                    continue

                should_update = force or is_missing_or_invalid_coordinate(
                    airport.latitude,
                    airport.longitude,
                )

                if not should_update:
                    skipped += 1
                    self.stdout.write(
                        f"Skipped: {iata_code} already has coordinates "
                        f"({airport.latitude}, {airport.longitude})"
                    )
                    continue

                old_latitude = airport.latitude
                old_longitude = airport.longitude

                airport.latitude = Decimal(data["latitude"])
                airport.longitude = Decimal(data["longitude"])

                if not airport.name or airport.name.strip().lower() in ["unknown", "n/a", "none", "-"]:
                    airport.name = data["name"]

                if not airport.city or airport.city.strip().lower() in ["unknown", "n/a", "none", "-"]:
                    airport.city = data["city"]

                if not airport.country or airport.country.strip().lower() in ["unknown", "n/a", "none", "-"]:
                    airport.country = data["country"]

                self.stdout.write(
                    f"{'Would update' if dry_run else 'Updated'}: "
                    f"{iata_code} | "
                    f"{old_latitude}, {old_longitude} -> "
                    f"{airport.latitude}, {airport.longitude}"
                )

                if not dry_run:
                    airport.save(
                        update_fields=[
                            "latitude",
                            "longitude",
                            "name",
                            "city",
                            "country",
                            "updated_at",
                        ]
                    )

                updated += 1

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write("-" * 70)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run finished. Would update: {updated}, skipped: {skipped}, not found: {not_found}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done. Updated: {updated}, skipped: {skipped}, not found: {not_found}"
                )
            )