from django.core.management.base import BaseCommand, CommandError

from apps.integrations.services.opensky_service import OpenSkyService, OpenSkyServiceError


class Command(BaseCommand):
    help = "Synchronize live aircraft positions from OpenSky into local Flight records."

    def handle(self, *args, **options):
        service = OpenSkyService()

        if not service.is_configured():
            raise CommandError(
                "OpenSky is not configured. Add OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET to settings."
            )

        try:
            result = service.sync_live_states()
        except OpenSkyServiceError as exc:
            raise CommandError(str(exc))
        except Exception as exc:
            raise CommandError(f"Unexpected OpenSky sync failure: {exc}")

        self.stdout.write(self.style.SUCCESS("OpenSky synchronization completed."))
        self.stdout.write(f"States received: {result['states_received']}")
        self.stdout.write(f"Matched flights: {result['matched_flights']}")
        self.stdout.write(f"Updated flights: {result['updated_flights']}")

        if result["matched_details"]:
            self.stdout.write("")
            self.stdout.write("Matched flights detail:")
            for item in result["matched_details"][:20]:
                self.stdout.write(
                    f" - flight={item['flight_number']} | callsign={item['callsign']} | "
                    f"icao24={item['icao24']} | strategy={item['strategy']} | confidence={item['confidence']}"
                )

        if result["unmatched_flights"]:
            self.stdout.write("")
            self.stdout.write("Unmatched flights:")
            for item in result["unmatched_flights"][:20]:
                self.stdout.write(f" - {item}")

        diagnostics = result.get("diagnostics", {})

        self.stdout.write("")
        self.stdout.write("Diagnostic sample - Local flight numbers:")
        for item in diagnostics.get("sample_local_flights", [])[:20]:
            self.stdout.write(f"   {item}")

        self.stdout.write("")
        self.stdout.write("Diagnostic sample - OpenSky callsigns:")
        for item in diagnostics.get("sample_opensky_callsigns", [])[:20]:
            self.stdout.write(f"   {item}")

        self.stdout.write("")
        self.stdout.write("Common exact matches:")
        common_exact = diagnostics.get("common_exact", [])
        if common_exact:
            for item in common_exact[:20]:
                self.stdout.write(f"   {item}")
        else:
            self.stdout.write("   none")

        self.stdout.write("")
        self.stdout.write("Common numeric suffixes:")
        common_digits = diagnostics.get("common_digits", [])
        if common_digits:
            for item in common_digits[:20]:
                self.stdout.write(f"   {item}")
        else:
            self.stdout.write("   none")