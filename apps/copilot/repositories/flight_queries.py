from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.utils import timezone

from apps.flights.models import Flight


class FlightQueries:
    ACTIVE_STATUSES = ["scheduled", "boarding", "departed", "in_air", "delayed"]
    COMPLETED_STATUSES = ["landed", "cancelled"]
    DISRUPTION_STATUSES = ["delayed", "cancelled"]

    def get_operational_summary(self) -> dict:
        queryset = Flight.objects.all()

        summary = queryset.aggregate(
            total_flights=Count("id"),
            scheduled_count=Count("id", filter=Q(status="scheduled")),
            boarding_count=Count("id", filter=Q(status="boarding")),
            departed_count=Count("id", filter=Q(status="departed")),
            in_air_count=Count("id", filter=Q(status="in_air")),
            landed_count=Count("id", filter=Q(status="landed")),
            delayed_count=Count("id", filter=Q(status="delayed")),
            cancelled_count=Count("id", filter=Q(status="cancelled")),
            active_count=Count("id", filter=Q(status__in=self.ACTIVE_STATUSES)),
            completed_count=Count("id", filter=Q(status__in=self.COMPLETED_STATUSES)),
            api_flights=Count("id", filter=Q(source_type="api")),
            local_flights=Count("id", filter=Q(source_type="local")),
            live_tracked_count=Count(
                "id",
                filter=Q(live_latitude__isnull=False, live_longitude__isnull=False),
            ),
        )

        total_flights = summary["total_flights"] or 0
        delayed_count = summary["delayed_count"] or 0
        cancelled_count = summary["cancelled_count"] or 0
        active_count = summary["active_count"] or 0
        api_flights = summary["api_flights"] or 0
        local_flights = summary["local_flights"] or 0
        live_tracked_count = summary["live_tracked_count"] or 0

        summary["critical_count"] = delayed_count + cancelled_count
        summary["delay_rate"] = self._safe_rate(delayed_count, total_flights)
        summary["cancellation_rate"] = self._safe_rate(cancelled_count, total_flights)
        summary["active_rate"] = self._safe_rate(active_count, total_flights)
        summary["api_rate"] = self._safe_rate(api_flights, total_flights)
        summary["local_rate"] = self._safe_rate(local_flights, total_flights)
        summary["live_tracked_rate"] = self._safe_rate(live_tracked_count, total_flights)
        summary["dominant_status"] = self._get_dominant_status(summary)

        return summary

    def get_delayed_flights(self, limit: int = 10) -> list[dict]:
        queryset = (
            Flight.objects.filter(status="delayed")
            .select_related("airline", "origin_airport", "destination_airport")
            .order_by("-scheduled_departure")[:limit]
        )
        return [self._serialize_flight_record(flight) for flight in queryset]

    def get_cancelled_flights(self, limit: int = 10) -> list[dict]:
        queryset = (
            Flight.objects.filter(status="cancelled")
            .select_related("airline", "origin_airport", "destination_airport")
            .order_by("-scheduled_departure")[:limit]
        )
        return [self._serialize_flight_record(flight) for flight in queryset]

    def get_priority_flights(self, limit: int = 10) -> list[dict]:
        queryset = (
            Flight.objects.filter(status__in=self.DISRUPTION_STATUSES)
            .select_related("airline", "origin_airport", "destination_airport")
            .annotate(
                priority_rank=Case(
                    When(status="cancelled", then=Value(0)),
                    When(status="delayed", then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            )
            .order_by("priority_rank", "-scheduled_departure")[:limit]
        )
        return [self._serialize_flight_record(flight) for flight in queryset]

    def get_source_breakdown(self) -> dict:
        queryset = Flight.objects.all()

        total_flights = queryset.count()
        api_flights = queryset.filter(source_type="api").count()
        local_flights = queryset.filter(source_type="local").count()

        return {
            "total_flights": total_flights,
            "api_flights": api_flights,
            "local_flights": local_flights,
            "api_rate": self._safe_rate(api_flights, total_flights),
            "local_rate": self._safe_rate(local_flights, total_flights),
        }

    def get_critical_attention_snapshot(self, limit: int = 5) -> dict:
        delayed_count = Flight.objects.filter(status="delayed").count()
        cancelled_count = Flight.objects.filter(status="cancelled").count()
        critical_count = delayed_count + cancelled_count

        return {
            "delayed_count": delayed_count,
            "cancelled_count": cancelled_count,
            "critical_count": critical_count,
            "priority_flights": self.get_priority_flights(limit=limit),
        }

    def get_top_airlines(self, limit: int = 5) -> list[dict]:
        queryset = (
            Flight.objects.exclude(airline__isnull=True)
            .values("airline__id", "airline__name")
            .annotate(flight_count=Count("id"))
            .order_by("-flight_count", "airline__name")[:limit]
        )

        return [
            {
                "airline_id": row["airline__id"],
                "airline_name": row["airline__name"] or "Unknown airline",
                "flight_count": row["flight_count"],
            }
            for row in queryset
        ]

    def get_top_airports(self, limit: int = 5) -> list[dict]:
        origin_queryset = (
            Flight.objects.exclude(origin_airport__isnull=True)
            .values("origin_airport__id", "origin_airport__name", "origin_airport__iata_code")
            .annotate(flight_count=Count("id"))
            .order_by("-flight_count", "origin_airport__name")[:limit]
        )

        return [
            {
                "airport_id": row["origin_airport__id"],
                "airport_name": row["origin_airport__name"] or "Unknown airport",
                "airport_code": row["origin_airport__iata_code"] or "",
                "flight_count": row["flight_count"],
            }
            for row in origin_queryset
        ]

    def get_top_routes(self, limit: int = 5) -> list[dict]:
        queryset = (
            Flight.objects.exclude(origin_airport__isnull=True)
            .exclude(destination_airport__isnull=True)
            .values(
                "origin_airport__iata_code",
                "destination_airport__iata_code",
            )
            .annotate(flight_count=Count("id"))
            .order_by("-flight_count", "origin_airport__iata_code", "destination_airport__iata_code")[:limit]
        )

        return [
            {
                "route": f"{row['origin_airport__iata_code']} → {row['destination_airport__iata_code']}",
                "origin_iata": row["origin_airport__iata_code"],
                "destination_iata": row["destination_airport__iata_code"],
                "flight_count": row["flight_count"],
            }
            for row in queryset
        ]

    def get_todays_flights(self, limit: int = 15) -> list[dict]:
        today = timezone.localdate()

        queryset = (
            Flight.objects.filter(scheduled_departure__date=today)
            .select_related("airline", "origin_airport", "destination_airport")
            .order_by("scheduled_departure")[:limit]
        )

        return [self._serialize_flight_record(flight) for flight in queryset]

    def count_todays_flights(self) -> int:
        today = timezone.localdate()
        return Flight.objects.filter(scheduled_departure__date=today).count()

    def get_flights_by_status(self, status: str, limit: int = 15) -> list[dict]:
        queryset = (
            Flight.objects.filter(status=status)
            .select_related("airline", "origin_airport", "destination_airport")
            .order_by("-scheduled_departure")[:limit]
        )
        return [self._serialize_flight_record(flight) for flight in queryset]

    def count_flights_by_status(self, status: str) -> int:
        return Flight.objects.filter(status=status).count()

    def get_flights_by_airline_name(self, airline_name: str, limit: int = 15) -> list[dict]:
        queryset = (
            Flight.objects.filter(airline__name__icontains=airline_name)
            .select_related("airline", "origin_airport", "destination_airport")
            .order_by("-scheduled_departure")[:limit]
        )
        return [self._serialize_flight_record(flight) for flight in queryset]

    def count_flights_by_airline_name(self, airline_name: str) -> int:
        return Flight.objects.filter(airline__name__icontains=airline_name).count()

    def _serialize_flight_record(self, flight: Flight) -> dict:
        return {
            "id": flight.id,
            "flight_number": flight.flight_number,
            "airline": str(flight.airline) if flight.airline_id else None,
            "route": flight.route,
            "origin_iata": flight.origin_airport.iata_code if flight.origin_airport_id else None,
            "destination_iata": flight.destination_airport.iata_code if flight.destination_airport_id else None,
            "status": flight.status,
            "status_label": flight.get_status_display(),
            "source_type": flight.source_type,
            "source_type_label": flight.get_source_type_display(),
            "scheduled_departure": flight.scheduled_departure.isoformat() if flight.scheduled_departure else None,
            "scheduled_arrival": flight.scheduled_arrival.isoformat() if flight.scheduled_arrival else None,
            "actual_departure": flight.actual_departure.isoformat() if flight.actual_departure else None,
            "actual_arrival": flight.actual_arrival.isoformat() if flight.actual_arrival else None,
            "departure_delay_minutes": flight.get_departure_delay_minutes(),
            "arrival_delay_minutes": flight.get_arrival_delay_minutes(),
            "is_live_tracked": flight.is_live_tracked,
            "last_synced_at": flight.last_synced_at.isoformat() if flight.last_synced_at else None,
        }

    def _get_dominant_status(self, summary: dict) -> str | None:
        status_counts = {
            "scheduled": summary.get("scheduled_count", 0),
            "boarding": summary.get("boarding_count", 0),
            "departed": summary.get("departed_count", 0),
            "in_air": summary.get("in_air_count", 0),
            "landed": summary.get("landed_count", 0),
            "delayed": summary.get("delayed_count", 0),
            "cancelled": summary.get("cancelled_count", 0),
        }

        if not any(status_counts.values()):
            return None

        return max(status_counts, key=status_counts.get)

    def _safe_rate(self, numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round((numerator / denominator) * 100, 1)