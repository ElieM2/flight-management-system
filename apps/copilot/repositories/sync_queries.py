from django.db.models import Count, Q, Sum

from apps.integrations.models import ApiSyncLog


class SyncQueries:
    def get_latest_log(self) -> dict | None:
        log = ApiSyncLog.objects.order_by("-started_at").first()
        if not log:
            return None
        return self._serialize_log(log)

    def get_recent_logs(self, limit: int = 5) -> list[dict]:
        queryset = ApiSyncLog.objects.order_by("-started_at")[:limit]
        return [self._serialize_log(log) for log in queryset]

    def get_sync_status_summary(self) -> dict:
        queryset = ApiSyncLog.objects.all()

        aggregates = queryset.aggregate(
            total_logs=Count("id"),
            success_count=Count("id", filter=Q(status="success")),
            failed_count=Count("id", filter=Q(status="failed")),
            total_records_received=Sum("records_received"),
            total_records_created=Sum("records_created"),
            total_records_updated=Sum("records_updated"),
        )

        total_logs = aggregates["total_logs"] or 0
        success_count = aggregates["success_count"] or 0
        failed_count = aggregates["failed_count"] or 0

        last_success = queryset.filter(status="success").order_by("-started_at").first()
        latest_log = queryset.order_by("-started_at").first()

        return {
            "total_logs": total_logs,
            "success_count": success_count,
            "failed_count": failed_count,
            "success_rate": self._safe_rate(success_count, total_logs),
            "failure_rate": self._safe_rate(failed_count, total_logs),
            "total_records_received": aggregates["total_records_received"] or 0,
            "total_records_created": aggregates["total_records_created"] or 0,
            "total_records_updated": aggregates["total_records_updated"] or 0,
            "latest_log": self._serialize_log(latest_log) if latest_log else None,
            "last_successful_log": self._serialize_log(last_success) if last_success else None,
        }

    def _serialize_log(self, log: ApiSyncLog) -> dict:
        duration_seconds = None
        if log.finished_at and log.started_at:
            duration_seconds = int((log.finished_at - log.started_at).total_seconds())

        return {
            "id": log.id,
            "provider_name": log.provider_name,
            "sync_type": log.sync_type,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "finished_at": log.finished_at.isoformat() if log.finished_at else None,
            "status": log.status,
            "status_label": log.get_status_display(),
            "records_received": log.records_received,
            "records_created": log.records_created,
            "records_updated": log.records_updated,
            "message": log.message,
            "duration_seconds": duration_seconds,
        }

    def _safe_rate(self, numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round((numerator / denominator) * 100, 1)