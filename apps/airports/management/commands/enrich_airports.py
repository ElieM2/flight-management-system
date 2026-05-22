from django.core.management.base import BaseCommand, CommandError

from apps.integrations.services.airport_enrichment_service import AirportEnrichmentService


class Command(BaseCommand):
    help = 'Enrich incomplete airports using AirLabs airport data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit-airports',
            type=int,
            default=None,
            help='Maximum number of airports to process.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without saving them to the database.',
        )
        parser.add_argument(
            '--hide-details',
            action='store_true',
            help='Hide detailed per-airport output.',
        )

    def _validate_arguments(self, airport_limit):
        if airport_limit is not None and airport_limit <= 0:
            raise CommandError('--limit-airports must be a positive integer.')

    def _print_header(self, airport_limit, dry_run):
        mode_label = 'DRY RUN' if dry_run else 'LIVE RUN'

        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('=== Airport Enrichment ==='))
        self.stdout.write(f"Mode: {mode_label}")
        self.stdout.write(f"Airport limit: {airport_limit if airport_limit is not None else 'all'}")
        self.stdout.write('')

    def _print_summary(self, stats, dry_run):
        if dry_run:
            self.stdout.write(self.style.SUCCESS('Airport enrichment dry-run finished.'))
        else:
            self.stdout.write(self.style.SUCCESS('Airport enrichment finished.'))

        self.stdout.write(f"Processed: {stats.get('processed', 0)}")
        self.stdout.write(f"Updated: {stats.get('updated', 0)}")
        self.stdout.write(f"No candidates: {stats.get('no_candidates', 0)}")
        self.stdout.write(f"No new data: {stats.get('no_new_data', 0)}")
        self.stdout.write(f"Already complete: {stats.get('already_complete', 0)}")
        self.stdout.write(f"Errors: {stats.get('errors', 0)}")
        self.stdout.write('')

    def _print_details(self, stats):
        details = stats.get('details', [])
        if not details:
            self.stdout.write('No detailed results available.')
            return

        self.stdout.write('Detailed results:')
        for item in details:
            airport = item.get('airport', 'Unknown airport')
            reason = item.get('reason', 'unknown')
            fields_updated = item.get('fields_updated') or []
            fields = ', '.join(fields_updated) if fields_updated else 'none'

            if reason == 'enriched':
                line = f"- {airport} | enriched | fields: {fields}"
                self.stdout.write(self.style.SUCCESS(line))
            elif str(reason).startswith('error:'):
                line = f"- {airport} | {reason} | fields: {fields}"
                self.stdout.write(self.style.ERROR(line))
            else:
                line = f"- {airport} | {reason} | fields: {fields}"
                self.stdout.write(line)

    def handle(self, *args, **options):
        airport_limit = options['limit_airports']
        dry_run = options['dry_run']
        hide_details = options['hide_details']

        self._validate_arguments(airport_limit)
        self._print_header(airport_limit=airport_limit, dry_run=dry_run)

        try:
            service = AirportEnrichmentService()
        except Exception as exc:
            raise CommandError(
                f"Unable to initialize airport enrichment service: {exc}"
            ) from exc

        try:
            stats = service.enrich_incomplete_airports(
                airport_limit=airport_limit,
                dry_run=dry_run,
            )
        except Exception as exc:
            raise CommandError(
                f"Airport enrichment failed during execution: {exc}"
            ) from exc

        self._print_summary(stats=stats, dry_run=dry_run)

        if not hide_details:
            self._print_details(stats)

        if stats.get('errors', 0) > 0:
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING(
                    'Airport enrichment completed with some errors. Review the detailed results above.'
                )
            )