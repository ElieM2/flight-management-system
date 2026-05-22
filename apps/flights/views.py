from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from .models import Flight


FLIGHT_STATUSES = [
    "scheduled",
    "boarding",
    "departed",
    "in_air",
    "landed",
    "delayed",
    "cancelled",
]


def _safe_rate(value, total):
    if not total:
        return 0
    return round((value / total) * 100, 1)


def flight_list(request):
    query = request.GET.get("q", "").strip()
    source_type = request.GET.get("source_type", "").strip().lower()
    status = request.GET.get("status", "").strip().lower()

    base_flights = Flight.objects.select_related(
        "airline",
        "aircraft",
        "origin_airport",
        "destination_airport",
    )

    flights = base_flights.order_by("-scheduled_departure", "-id")

    if query:
        flights = flights.filter(
            Q(flight_number__icontains=query)
            | Q(airline__name__icontains=query)
            | Q(origin_airport__name__icontains=query)
            | Q(destination_airport__name__icontains=query)
            | Q(origin_airport__city__icontains=query)
            | Q(destination_airport__city__icontains=query)
            | Q(origin_airport__iata_code__icontains=query)
            | Q(destination_airport__iata_code__icontains=query)
            | Q(origin_airport__icao_code__icontains=query)
            | Q(destination_airport__icao_code__icontains=query)
            | Q(aircraft__model__icontains=query)
            | Q(aircraft__registration_number__icontains=query)
        )

    if source_type in ["local", "api"]:
        flights = flights.filter(source_type=source_type)
    else:
        source_type = ""

    if status in FLIGHT_STATUSES:
        flights = flights.filter(status=status)
    else:
        status = ""

    total_flights = base_flights.count()
    visible_flights_count = flights.count()

    active_flights_count = flights.filter(
        status__in=["boarding", "departed", "in_air"]
    ).count()

    scheduled_count = flights.filter(status="scheduled").count()
    boarding_count = flights.filter(status="boarding").count()
    departed_count = flights.filter(status="departed").count()
    in_air_count = flights.filter(status="in_air").count()
    delayed_count = flights.filter(status="delayed").count()
    cancelled_count = flights.filter(status="cancelled").count()
    landed_count = flights.filter(status="landed").count()

    api_count = flights.filter(source_type="api").count()
    local_count = flights.filter(source_type="local").count()

    disruption_count = delayed_count + cancelled_count
    disruption_rate = _safe_rate(disruption_count, visible_flights_count)

    on_time_count = visible_flights_count - disruption_count
    on_time_rate = _safe_rate(on_time_count, visible_flights_count)

    api_rate = _safe_rate(api_count, visible_flights_count)

    status_rows_raw = (
        flights.values("status")
        .annotate(total=Count("id"))
        .order_by("status")
    )
    status_map = {item["status"]: item["total"] for item in status_rows_raw}

    paginator = Paginator(flights, 8)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "flights": page_obj.object_list,
        "page_obj": page_obj,

        "query": query,
        "selected_source_type": source_type,
        "selected_status": status,

        "total_flights": total_flights,
        "visible_flights_count": visible_flights_count,

        "active_flights_count": active_flights_count,
        "scheduled_count": scheduled_count,
        "boarding_count": boarding_count,
        "departed_count": departed_count,
        "in_air_count": in_air_count,
        "delayed_count": delayed_count,
        "cancelled_count": cancelled_count,
        "landed_count": landed_count,

        "api_count": api_count,
        "local_count": local_count,

        "disruption_count": disruption_count,
        "disruption_rate": disruption_rate,
        "on_time_rate": on_time_rate,
        "api_rate": api_rate,

        "status_map": status_map,
    }

    return render(request, "flights/list.html", context)


def flight_detail(request, pk):
    flight = get_object_or_404(
        Flight.objects.select_related(
            "airline",
            "aircraft",
            "origin_airport",
            "destination_airport",
        ).prefetch_related("status_history"),
        pk=pk,
    )

    history_entries = flight.status_history.all().order_by("-changed_at")
    latest_history = history_entries.first()

    departure_delay_minutes = flight.get_departure_delay_minutes()
    arrival_delay_minutes = flight.get_arrival_delay_minutes()

    disruption_events = history_entries.filter(is_disruption_event=True).count()
    schedule_change_events = history_entries.filter(schedule_changed=True).count()
    live_update_events = history_entries.filter(live_data_changed=True).count()
    status_change_events = history_entries.filter(status_changed=True).count()

    current_operational_note = (
        "This flight is currently listed without a visible operational escalation."
    )

    if flight.status == "cancelled":
        current_operational_note = (
            "This flight is cancelled. The record should be reviewed for passenger impact, "
            "route disruption and operational recovery."
        )
    elif flight.status == "delayed":
        current_operational_note = (
            "This flight is delayed. Schedule pressure and possible downstream impact should be checked."
        )
    elif flight.status == "in_air":
        current_operational_note = (
            "This flight is airborne and remains part of the active monitoring picture until arrival."
        )
    elif flight.status == "boarding":
        current_operational_note = (
            "Boarding is in progress. Departure readiness should remain under observation."
        )
    elif flight.status == "departed":
        current_operational_note = (
            "This flight has departed and should be followed until the route progression is stable."
        )
    elif flight.status == "landed":
        current_operational_note = (
            "This flight has landed. The record remains useful for traceability and post-operation review."
        )
    elif flight.status == "scheduled":
        current_operational_note = (
            "This flight is scheduled. Timing, route and source data are available for consultation."
        )

    context = {
        "flight": flight,
        "history_entries": history_entries,
        "latest_history": latest_history,

        "departure_delay_minutes": departure_delay_minutes,
        "arrival_delay_minutes": arrival_delay_minutes,

        "disruption_events": disruption_events,
        "schedule_change_events": schedule_change_events,
        "live_update_events": live_update_events,
        "status_change_events": status_change_events,

        "current_operational_note": current_operational_note,
    }

    return render(request, "flights/detail.html", context)