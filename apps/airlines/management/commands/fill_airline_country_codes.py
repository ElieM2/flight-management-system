from django.core.management.base import BaseCommand
from apps.airlines.models import Airline

COUNTRY_NAME_TO_CODE = {
    "Afghanistan": "AF",
    "Albania": "AL",
    "Algeria": "DZ",
    "Argentina": "AR",
    "Armenia": "AM",
    "Australia": "AU",
    "Austria": "AT",
    "Azerbaijan": "AZ",
    "Bahrain": "BH",
    "Bangladesh": "BD",
    "Belarus": "BY",
    "Belgium": "BE",
    "Brazil": "BR",
    "Bulgaria": "BG",
    "Canada": "CA",
    "Chile": "CL",
    "China": "CN",
    "Colombia": "CO",
    "Croatia": "HR",
    "Cyprus": "CY",
    "Czech Republic": "CZ",
    "Denmark": "DK",
    "Egypt": "EG",
    "Estonia": "EE",
    "Ethiopia": "ET",
    "Finland": "FI",
    "France": "FR",
    "Georgia": "GE",
    "Germany": "DE",
    "Greece": "GR",
    "Hong Kong": "HK",
    "Hungary": "HU",
    "Iceland": "IS",
    "India": "IN",
    "Indonesia": "ID",
    "Iran": "IR",
    "Iraq": "IQ",
    "Ireland": "IE",
    "Israel": "IL",
    "Italy": "IT",
    "Japan": "JP",
    "Jordan": "JO",
    "Kazakhstan": "KZ",
    "Kenya": "KE",
    "Kuwait": "KW",
    "Latvia": "LV",
    "Lebanon": "LB",
    "Lithuania": "LT",
    "Luxembourg": "LU",
    "Madagascar": "MG",
    "Malaysia": "MY",
    "Malta": "MT",
    "Mauritius": "MU",
    "Mexico": "MX",
    "Moldova": "MD",
    "Mongolia": "MN",
    "Morocco": "MA",
    "Netherlands": "NL",
    "New Zealand": "NZ",
    "Nigeria": "NG",
    "Norway": "NO",
    "Pakistan": "PK",
    "Philippines": "PH",
    "Poland": "PL",
    "Portugal": "PT",
    "Qatar": "QA",
    "Romania": "RO",
    "Russia": "RU",
    "Russian Federation": "RU",
    "Saudi Arabia": "SA",
    "Serbia": "RS",
    "Seychelles": "SC",
    "Singapore": "SG",
    "Slovakia": "SK",
    "Slovenia": "SI",
    "South Africa": "ZA",
    "South Korea": "KR",
    "Spain": "ES",
    "Sri Lanka": "LK",
    "Sweden": "SE",
    "Switzerland": "CH",
    "Taiwan": "TW",
    "Thailand": "TH",
    "Tunisia": "TN",
    "Turkey": "TR",
    "Türkiye": "TR",
    "Ukraine": "UA",
    "United Arab Emirates": "AE",
    "UAE": "AE",
    "United Kingdom": "GB",
    "UK": "GB",
    "United States": "US",
    "United States of America": "US",
    "USA": "US",
    "Uzbekistan": "UZ",
    "Vietnam": "VN",
}

AIRLINE_NAME_TO_CODE = {
    "ANA": ("Japan", "JP"),
    "All Nippon Airways": ("Japan", "JP"),

    "ASL Airlines Belgium": ("Belgium", "BE"),
    "ASL Airlines France": ("France", "FR"),
    "ASL Airlines Ireland": ("Ireland", "IE"),

    "Aeroflot": ("Russia", "RU"),
    "Aerolineas Argentinas": ("Argentina", "AR"),
    "Aeromexico": ("Mexico", "MX"),
    "Air Baltic": ("Latvia", "LV"),
    "Air China LTD": ("China", "CN"),
    "Air France": ("France", "FR"),
    "Air India": ("India", "IN"),
    "Air Madagascar": ("Madagascar", "MG"),
    "Air Mauritius": ("Mauritius", "MU"),
    "Air New Zealand": ("New Zealand", "NZ"),
    "Air Serbia": ("Serbia", "RS"),
    "Air Seychelles": ("Seychelles", "SC"),
    "Airhub Airlines Ltd (Malta)": ("Malta", "MT"),

    "Allegiant Air": ("United States", "US"),
    "American Airlines": ("United States", "US"),
    "Beijing Capital Airlines": ("China", "CN"),
    "British Airways": ("United Kingdom", "GB"),

    "China Eastern Airlines": ("China", "CN"),
    "China Express Air": ("China", "CN"),
    "China Southern Airlines Cargo": ("China", "CN"),

    "DHL Air": ("United Kingdom", "GB"),
    "Delta Air Lines": ("United States", "US"),

    "El Al": ("Israel", "IL"),
    "Etihad Airways": ("United Arab Emirates", "AE"),
    "Emirates": ("United Arab Emirates", "AE"),
    "Eurowings": ("Germany", "DE"),

    "FedEx": ("United States", "US"),
    "FedEx Express": ("United States", "US"),

    "Garuda Indonesia": ("Indonesia", "ID"),
    "Gol": ("Brazil", "BR"),
    "Hawaiian Airlines": ("United States", "US"),
    "Iberia": ("Spain", "ES"),
    "Icelandair": ("Iceland", "IS"),
    "IndiGo": ("India", "IN"),
    "Jambojet": ("Kenya", "KE"),
    "Japan Airlines": ("Japan", "JP"),
    "JetBlue Airways": ("United States", "US"),
    "Jetstar": ("Australia", "AU"),
    "Juneyao Airlines": ("China", "CN"),

    "KLM": ("Netherlands", "NL"),
    "Kenya Airways": ("Kenya", "KE"),
    "Korean Air": ("South Korea", "KR"),

    "LAM": ("Mozambique", "MZ"),
    "LATAM Airlines": ("Chile", "CL"),
    "LOT Polish Airlines": ("Poland", "PL"),
    "Lion Air": ("Indonesia", "ID"),
    "Lufthansa": ("Germany", "DE"),

    "Malaysia Airlines": ("Malaysia", "MY"),
    "Miami Air International": ("United States", "US"),
    "Miat - Mongolian Airlines": ("Mongolia", "MN"),

    "National Jet Express": ("Australia", "AU"),

    "Philippine Airlines": ("Philippines", "PH"),
    "Philippines AirAsia": ("Philippines", "PH"),
    "Pobeda": ("Russia", "RU"),

    "Qantas": ("Australia", "AU"),
    "Qatar Airways": ("Qatar", "QA"),

    "Rossiya Airlines": ("Russia", "RU"),
    "Ryanair": ("Ireland", "IE"),

    "SAS": ("Sweden", "SE"),
    "Saudia": ("Saudi Arabia", "SA"),
    "Shandong Airlines": ("China", "CN"),
    "Shenzhen Airlines": ("China", "CN"),
    "Sichuan Airlines": ("China", "CN"),
    "Singapore Airlines": ("Singapore", "SG"),
    "SriLankan Airlines": ("Sri Lanka", "LK"),
    "Star Air": ("India", "IN"),
    "Super Air Jet": ("Indonesia", "ID"),
    "Swiftair": ("Spain", "ES"),

    "TAP Air Portugal": ("Portugal", "PT"),
    "Tianjin Airlines": ("China", "CN"),
    "Tibet Airlines": ("China", "CN"),
    "Turkish Airlines": ("Turkey", "TR"),

    "UPS Airlines": ("United States", "US"),
    "United Airlines": ("United States", "US"),

    "VietJet Air": ("Vietnam", "VN"),
    "Virgin Atlantic": ("United Kingdom", "GB"),
    "Virgin Australia": ("Australia", "AU"),

    "WestJet": ("Canada", "CA"),
    "Wings Air": ("Indonesia", "ID"),
    "Xiamen Airlines": ("China", "CN"),
}

class Command(BaseCommand):
    help = "Fill missing airline country_code values from country names and known airline names."

    def handle(self, *args, **options):
        updated = 0
        skipped = 0

        airlines = Airline.objects.all().order_by("name")

        for airline in airlines:
            country = (airline.country or "").strip()
            current_code = (airline.country_code or "").strip()

            if current_code:
                skipped += 1
                continue

            resolved_country = country
            resolved_code = None

            if airline.name in AIRLINE_NAME_TO_CODE:
                resolved_country, resolved_code = AIRLINE_NAME_TO_CODE[airline.name]
            elif country in COUNTRY_NAME_TO_CODE:
                resolved_code = COUNTRY_NAME_TO_CODE[country]

            if not resolved_code:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipped: {airline.name} | country='{country or 'empty'}'"
                    )
                )
                continue

            airline.country = resolved_country
            airline.country_code = resolved_code
            airline.save(update_fields=["country", "country_code", "updated_at"])

            updated += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"Updated: {airline.name} -> {resolved_country} / {resolved_code}"
                )
            )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Done. Updated: {updated}"))
        self.stdout.write(self.style.WARNING(f"Skipped: {skipped}"))