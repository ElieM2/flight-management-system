from itertools import cycle

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.aircraft.models import Aircraft
from apps.flights.models import Flight


class Command(BaseCommand):
    help = "Assign available aircraft to flights that do not have aircraft linked."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            choices=["all", "local", "api"],
            default="all",
            help="Limit assignment by flight source type.",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without saving changes.",
        )

    def handle(self, *args, **options):
        source = options["source"]
        dry_run = options["dry_run"]

        flights = Flight.objects.select_related("airline").filter(aircraft__isnull=True)

        if source != "all":
            flights = flights.filter(source_type=source)

        flights = flights.order_by("airline__name", "scheduled_departure", "id")

        if not flights.exists():
            self.stdout.write(self.style.SUCCESS("No flights without aircraft found."))
            return

        aircraft_queryset = Aircraft.objects.select_related("airline").all().order_by(
            "airline__name",
            "model",
            "registration_number",
            "id",
        )

        if not aircraft_queryset.exists():
            self.stdout.write(
                self.style.ERROR(
                    "No aircraft found. Create aircraft records first before assigning them to flights."
                )
            )
            return

        updated = 0
        skipped = 0

        aircraft_by_airline_id = {}

        for aircraft in aircraft_queryset:
            airline_id = getattr(aircraft, "airline_id", None)
            if airline_id:
                aircraft_by_airline_id.setdefault(airline_id, []).append(aircraft)

        fallback_aircraft_cycle = cycle(list(aircraft_queryset))

        self.stdout.write("")
        self.stdout.write("Assigning missing aircraft...")
        self.stdout.write("-" * 60)

        with transaction.atomic():
            for flight in flights:
                selected_aircraft = None

                if flight.airline_id in aircraft_by_airline_id:
                    airline_aircraft_list = aircraft_by_airline_id[flight.airline_id]
                    selected_aircraft = airline_aircraft_list[updated % len(airline_aircraft_list)]
                else:
                    selected_aircraft = next(fallback_aircraft_cycle)

                if not selected_aircraft:
                    skipped += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipped: {flight.flight_number} | no aircraft candidate"
                        )
                    )
                    continue

                self.stdout.write(
                    f"{'Would update' if dry_run else 'Updated'}: "
                    f"{flight.flight_number} -> {selected_aircraft.model}"
                    f"{' / ' + selected_aircraft.registration_number if getattr(selected_aircraft, 'registration_number', None) else ''}"
                )

                if not dry_run:
                    flight.aircraft = selected_aircraft
                    flight.save(update_fields=["aircraft", "updated_at"])

                updated += 1

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write("-" * 60)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run finished. Would update: {updated}, skipped: {skipped}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done. Updated: {updated}, skipped: {skipped}"
                )
            )