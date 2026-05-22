from django.contrib.auth.decorators import login_required
from django.db.models import Case, Count, IntegerField, Value, When
from django.shortcuts import render
from django.utils.translation import gettext as _, ngettext

from apps.aircraft.models import Aircraft
from apps.airlines.models import Airline
from apps.airports.models import Airport
from apps.flights.models import Flight


STATUS_PRIORITY = {
    "cancelled": 100,
    "delayed": 90,
    "in_air": 70,
    "departed": 60,
    "boarding": 50,
    "scheduled": 30,
    "landed": 10,
}


STATUS_LABELS = {
    "scheduled": _("Scheduled"),
    "boarding": _("Boarding"),
    "departed": _("Departed"),
    "in_air": _("In Air"),
    "landed": _("Landed"),
    "delayed": _("Delayed"),
    "cancelled": _("Cancelled"),
}


def safe_rate(value, total):
    if not total:
        return 0

    return round((value / total) * 100, 1)


def get_status_label(status):
    return STATUS_LABELS.get(status, status.replace("_", " ").title())


def build_status_priority_case(include_source_bonus=False):
    priority_case = Case(
        *[
            When(status=status, then=Value(score))
            for status, score in STATUS_PRIORITY.items()
        ],
        default=Value(0),
        output_field=IntegerField(),
    )

    if not include_source_bonus:
        return priority_case

    source_bonus = Case(
        When(source_type="api", then=Value(5)),
        default=Value(0),
        output_field=IntegerField(),
    )

    return priority_case + source_bonus


def get_status_counts():
    raw_counts = {
        item["status"]: item["total"]
        for item in Flight.objects.values("status").annotate(total=Count("id"))
    }

    return {
        "scheduled_count": raw_counts.get("scheduled", 0),
        "boarding_count": raw_counts.get("boarding", 0),
        "departed_count": raw_counts.get("departed", 0),
        "in_air_count": raw_counts.get("in_air", 0),
        "landed_count": raw_counts.get("landed", 0),
        "delayed_count": raw_counts.get("delayed", 0),
        "cancelled_count": raw_counts.get("cancelled", 0),
    }


def get_route_label(route_data):
    if not route_data:
        return _("No route data")

    origin = route_data.get("origin_airport__iata_code") or "--"
    destination = route_data.get("destination_airport__iata_code") or "--"

    return f"{origin} → {destination}"


def get_high_risk_count():
    """
    Dashboard-level high-risk placeholder.

    The dashboard keeps the same global business rule used by the monitoring workspace:
    Critical = cancelled + high-risk flights.

    At this stage, high-risk flights are intentionally kept conservative in the dashboard.
    Cancelled flights are the confirmed recovery cases. Delayed flights remain attention-level
    records and are not counted as critical.
    """
    return 0


def get_global_operational_snapshot():
    total_flights = Flight.objects.count()
    total_airlines = Airline.objects.count()
    total_airports = Airport.objects.count()
    total_aircraft = Aircraft.objects.count()

    status_counts = get_status_counts()

    active_flights = Flight.objects.exclude(status__in=["landed", "cancelled"]).count()
    api_flights = Flight.objects.filter(source_type="api").count()
    local_flights = Flight.objects.filter(source_type="local").count()

    delayed_count = status_counts["delayed_count"]
    cancelled_count = status_counts["cancelled_count"]
    landed_count = status_counts["landed_count"]
    scheduled_count = status_counts["scheduled_count"]

    high_risk_count = get_high_risk_count()
    critical_count = cancelled_count + high_risk_count
    attention_count = delayed_count
    irregular_ops_count = critical_count + attention_count

    stable_count = landed_count + scheduled_count

    delay_rate = safe_rate(delayed_count, total_flights)
    cancellation_rate = safe_rate(cancelled_count, total_flights)
    active_rate = safe_rate(active_flights, total_flights)
    api_rate = safe_rate(api_flights, total_flights)
    local_rate = safe_rate(local_flights, total_flights)
    critical_rate = safe_rate(critical_count, total_flights)
    attention_rate = safe_rate(attention_count, total_flights)
    irregular_rate = safe_rate(irregular_ops_count, total_flights)

    most_active_airline = (
        Airline.objects.annotate(total=Count("flights"))
        .order_by("-total", "name")
        .first()
    )

    most_used_route = (
        Flight.objects.values(
            "origin_airport__iata_code",
            "destination_airport__iata_code",
        )
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    dominant_status = _("No data")

    if total_flights:
        dominant_status_item = (
            Flight.objects.values("status")
            .annotate(total=Count("id"))
            .order_by("-total", "status")
            .first()
        )

        if dominant_status_item:
            dominant_status = get_status_label(dominant_status_item["status"])

    if api_flights > local_flights:
        source_mode = _("API-led dataset")
        source_note = _("External synchronized records currently lead the operational dataset.")
    elif local_flights > api_flights:
        source_mode = _("Local-led dataset")
        source_note = _("Local records currently represent the largest part of the dataset.")
    else:
        source_mode = _("Balanced sources")
        source_note = _("API and local records are currently balanced or unavailable.")

    return {
        "total_flights": total_flights,
        "total_airlines": total_airlines,
        "total_airports": total_airports,
        "total_aircraft": total_aircraft,
        **status_counts,
        "active_flights": active_flights,
        "api_flights": api_flights,
        "local_flights": local_flights,
        "high_risk_count": high_risk_count,
        "critical_count": critical_count,
        "attention_count": attention_count,
        "irregular_ops_count": irregular_ops_count,
        "stable_count": stable_count,
        "delay_rate": delay_rate,
        "cancellation_rate": cancellation_rate,
        "active_rate": active_rate,
        "api_rate": api_rate,
        "local_rate": local_rate,
        "critical_rate": critical_rate,
        "attention_rate": attention_rate,
        "irregular_rate": irregular_rate,
        "most_active_airline": most_active_airline,
        "most_used_route": most_used_route,
        "most_used_route_label": get_route_label(most_used_route),
        "dominant_status": dominant_status,
        "source_mode": source_mode,
        "source_note": source_note,
    }


def build_preview_flights(limit=80):
    flights = (
        Flight.objects.select_related(
            "airline",
            "origin_airport",
            "destination_airport",
        )
        .order_by("-scheduled_departure")[:limit]
    )

    preview_flights = []

    for flight in flights:
        origin = flight.origin_airport
        destination = flight.destination_airport

        origin_lat = getattr(origin, "latitude", None)
        origin_lng = getattr(origin, "longitude", None)
        destination_lat = getattr(destination, "latitude", None)
        destination_lng = getattr(destination, "longitude", None)

        if None in [origin_lat, origin_lng, destination_lat, destination_lng]:
            continue

        preview_flights.append(
            {
                "flight_number": flight.flight_number,
                "airline": flight.airline.name if flight.airline else _("Unknown"),
                "status": flight.status,
                "status_display": str(flight.get_status_display()),
                "origin_code": origin.iata_code if origin else "---",
                "destination_code": destination.iata_code if destination else "---",
                "origin_lat": float(origin_lat),
                "origin_lng": float(origin_lng),
                "destination_lat": float(destination_lat),
                "destination_lng": float(destination_lng),
            }
        )

    return preview_flights


def get_operational_alert_context(snapshot):
    operational_alert_level = _("Normal")
    operational_alert_message = _("Operations are stable. Continue routine supervision.")
    dashboard_mode = _("Standard Control")
    priority_focus = _("Monitor active flights and keep route visibility stable.")

    cancelled_count = snapshot["cancelled_count"]
    delayed_count = snapshot["delayed_count"]
    critical_count = snapshot["critical_count"]
    attention_count = snapshot["attention_count"]
    in_air_count = snapshot["in_air_count"]
    active_flights = snapshot["active_flights"]

    if critical_count >= 3:
        operational_alert_level = _("High")
        operational_alert_message = _(
            "Recovery pressure is high. Review cancelled and high-risk flights before routine monitoring."
        )
        dashboard_mode = _("Recovery Supervision")
        priority_focus = _("Cancelled and high-risk recovery cases")

    elif critical_count >= 1 or attention_count >= 2:
        operational_alert_level = _("Medium")
        operational_alert_message = _(
            "Operational attention is required. Keep recovery cases and delayed flights under closer review."
        )
        dashboard_mode = _("Elevated Supervision")

        if critical_count > 0:
            priority_focus = _("Recovery cases requiring validation")
        else:
            priority_focus = _("Delayed flights requiring attention monitoring")

    elif in_air_count >= 5:
        operational_alert_level = _("Normal")
        operational_alert_message = _(
            "Traffic volume is active. Maintain supervision of airborne operations."
        )
        dashboard_mode = _("Live Traffic Monitoring")
        priority_focus = _("Airborne flights under active supervision")

    elif active_flights == 0:
        operational_alert_level = _("Normal")
        operational_alert_message = _(
            "No active operational pressure is visible in the current dataset."
        )
        dashboard_mode = _("Low Activity")
        priority_focus = _("Registry consistency and source coverage")

    return {
        "operational_alert_level": operational_alert_level,
        "operational_alert_message": operational_alert_message,
        "dashboard_mode": dashboard_mode,
        "priority_focus": priority_focus,
        "cancelled_count_for_alert": cancelled_count,
        "delayed_count_for_alert": delayed_count,
    }


def get_ranked_flights(limit=8, include_source_bonus=False):
    priority_score = build_status_priority_case(include_source_bonus=include_source_bonus)

    return (
        Flight.objects.select_related(
            "airline",
            "origin_airport",
            "destination_airport",
        )
        .annotate(priority_score=priority_score)
        .order_by("-priority_score", "-scheduled_departure")[:limit]
    )


def get_recent_flights(limit=8):
    return (
        Flight.objects.select_related(
            "airline",
            "origin_airport",
            "destination_airport",
        )
        .order_by("-scheduled_departure")[:limit]
    )


def build_command_insights(snapshot):
    insights = []

    if snapshot["critical_count"] > 0:
        count = snapshot["critical_count"]
        insights.append(
            ngettext(
                "%(count)s critical flight needs recovery handling.",
                "%(count)s critical flights need recovery handling.",
                count,
            ) % {"count": count}
        )

    if snapshot["cancelled_count"] > 0:
        count = snapshot["cancelled_count"]
        insights.append(
            ngettext(
                "%(count)s cancelled flight requires recovery review.",
                "%(count)s cancelled flights require recovery review.",
                count,
            ) % {"count": count}
        )

    if snapshot["delayed_count"] > 0:
        count = snapshot["delayed_count"]
        insights.append(
            ngettext(
                "%(count)s delayed flight remains under attention monitoring.",
                "%(count)s delayed flights remain under attention monitoring.",
                count,
            ) % {"count": count}
        )

    if snapshot["most_active_airline"]:
        insights.append(
            _("%(airline)s is the busiest airline in the current dataset.")
            % {"airline": snapshot["most_active_airline"].name}
        )

    if snapshot["most_used_route"]:
        insights.append(
            _("Most monitored route: %(route)s.")
            % {"route": snapshot["most_used_route_label"]}
        )

    if snapshot["api_flights"] > snapshot["local_flights"]:
        insights.append(_("API-synchronized flights currently dominate the dataset."))
    elif snapshot["local_flights"] > 0:
        insights.append(_("Local flight records remain important for operational continuity."))

    if snapshot["in_air_count"] > 0:
        count = snapshot["in_air_count"]
        insights.append(
            ngettext(
                "%(count)s flight is currently in air.",
                "%(count)s flights are currently in air.",
                count,
            ) % {"count": count}
        )

    if not insights:
        insights.append(_("No major operational pressure is visible in the current dataset."))

    return insights[:4]


def public_home_view(request):
    snapshot = get_global_operational_snapshot()
    preview_flights = build_preview_flights(limit=80)
    recent_flights = get_recent_flights(limit=8)

    public_highlights = []

    if snapshot["delayed_count"] > 0:
        count = snapshot["delayed_count"]
        public_highlights.append(
            ngettext(
                "%(count)s delayed flight is currently detected in the platform.",
                "%(count)s delayed flights are currently detected in the platform.",
                count,
            ) % {"count": count}
        )

    if snapshot["cancelled_count"] > 0:
        count = snapshot["cancelled_count"]
        public_highlights.append(
            ngettext(
                "%(count)s cancelled flight is visible in the operational dataset.",
                "%(count)s cancelled flights are visible in the operational dataset.",
                count,
            ) % {"count": count}
        )

    if snapshot["critical_count"] > 0:
        count = snapshot["critical_count"]
        public_highlights.append(
            ngettext(
                "%(count)s critical recovery case is visible in the operational dataset.",
                "%(count)s critical recovery cases are visible in the operational dataset.",
                count,
            ) % {"count": count}
        )

    if snapshot["most_active_airline"]:
        public_highlights.append(
            _("%(airline)s is currently the most active airline in the system.")
            % {"airline": snapshot["most_active_airline"].name}
        )

    if snapshot["most_used_route"]:
        public_highlights.append(
            _("The busiest route currently tracked is %(route)s.")
            % {"route": snapshot["most_used_route_label"]}
        )

    if not public_highlights:
        public_highlights.append(
            _("The platform is ready to centralize flights, monitoring, analytics and external synchronization.")
        )

    context = {
        **snapshot,
        "public_highlights": public_highlights,
        "preview_flights": preview_flights,
        "recent_flights": recent_flights,
    }

    return render(request, "home.html", context)


@login_required
def private_dashboard_view(request):
    snapshot = get_global_operational_snapshot()
    alert_context = get_operational_alert_context(snapshot)

    priority_flights = get_ranked_flights(limit=6, include_source_bonus=True)
    recent_flights = get_recent_flights(limit=8)
    command_insights = build_command_insights(snapshot)

    context = {
        **snapshot,
        **alert_context,
        "recent_flights": recent_flights,
        "priority_flights": priority_flights,
        "command_insights": command_insights,
    }

    return render(request, "dashboard/dashboard.html", context)