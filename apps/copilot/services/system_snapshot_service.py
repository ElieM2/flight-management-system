from django.utils import timezone

from apps.copilot.repositories.flight_queries import FlightQueries
from apps.copilot.repositories.sync_queries import SyncQueries


class SystemSnapshotService:
    def __init__(
        self,
        flight_queries: FlightQueries | None = None,
        sync_queries: SyncQueries | None = None,
    ):
        self.flight_queries = flight_queries or FlightQueries()
        self.sync_queries = sync_queries or SyncQueries()

    def build_snapshot(self) -> dict:
        return {
            "generated_at": timezone.now().isoformat(),
            "flight_summary": self.flight_queries.get_operational_summary(),
            "source_breakdown": self.flight_queries.get_source_breakdown(),
            "critical_attention": self.flight_queries.get_critical_attention_snapshot(limit=5),
            "api_sync_status": self.sync_queries.get_sync_status_summary(),
        }