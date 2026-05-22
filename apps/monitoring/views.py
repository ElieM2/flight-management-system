import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _, ngettext
from django.views.decorators.http import require_POST

from apps.flights.models import Flight
from apps.integrations.services.weather_service import WeatherHazardService

from .services import (
    build_attention_queue,
    build_map_context,
    build_next_operational_action,
    build_operational_recommendation,
    compute_operational_profile,
    compute_risk_score,
    compute_tracking_confidence,
    get_attention_label,
    get_flight_monitoring_reason,
    get_history_summary,
    get_monitoring_base_queryset,
    get_monitoring_snapshot,
    get_progress_by_status,
    get_risk_level,
    translate_priority_label,
    translate_risk_level,
)


@login_required
def monitoring_home(request):
    flights_queryset = get_monitoring_base_queryset()

    q = request.GET.get("q", "").strip()
    source = request.GET.get("source", "").strip().lower()
    status = request.GET.get("status", "").strip().lower()

    if q:
        flights_queryset = flights_queryset.filter(
            Q(flight_number__icontains=q)
            | Q(airline__name__icontains=q)
            | Q(origin_airport__name__icontains=q)
            | Q(destination_airport__name__icontains=q)
            | Q(origin_airport__iata_code__icontains=q)
            | Q(destination_airport__iata_code__icontains=q)
            | Q(origin_airport__icao_code__icontains=q)
            | Q(destination_airport__icao_code__icontains=q)
        )

    if source in ["api", "local"]:
        flights_queryset = flights_queryset.filter(source_type=source)

    allowed_statuses = [
        "scheduled",
        "boarding",
        "departed",
        "in_air",
        "landed",
        "delayed",
        "cancelled",
    ]

    if status in allowed_statuses:
        flights_queryset = flights_queryset.filter(status=status)

    flights_queryset = flights_queryset.order_by(
        "-scheduled_departure",
        "flight_number",
    )

    snapshot = get_monitoring_snapshot(flights_queryset)
    attention_queue = build_attention_queue(flights_queryset, limit=6)

    paginator = Paginator(flights_queryset, 8)
    page_number = request.GET.get("page", 1)

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    flights = list(page_obj.object_list)

    selected_flight = None
    flight_id = request.GET.get("flight")

    if flight_id and flight_id.isdigit():
        selected_flight = flights_queryset.filter(pk=int(flight_id)).first()

    if selected_flight is None:
        selected_flight = flights[0] if flights else None

    selected_flight_reason = None
    selected_flight_next_action = None
    selected_flight_priority = None
    selected_flight_priority_key = None

    if selected_flight:
        selected_flight_reason = get_flight_monitoring_reason(selected_flight)
        selected_flight_next_action = get_attention_label(selected_flight)

        try:
            selected_profile = compute_operational_profile(selected_flight)
            selected_flight_priority_key = selected_profile["posture"]
        except (TypeError, ValueError, AttributeError, KeyError):
            if selected_flight.status == "cancelled":
                selected_flight_priority_key = "critical"
            elif selected_flight.status == "delayed":
                selected_flight_priority_key = "attention"
            elif selected_flight.status == "in_air":
                selected_flight_priority_key = "active"
            elif selected_flight.status in ["boarding", "departed"]:
                selected_flight_priority_key = "attention"
            else:
                selected_flight_priority_key = "normal"

        selected_flight_priority = translate_priority_label(selected_flight_priority_key)

    query_params = request.GET.copy()

    if "page" in query_params:
        query_params.pop("page")

    pagination_query = query_params.urlencode()

    context = {
        "flights": flights,
        "page_obj": page_obj,
        "paginator": paginator,
        "pagination_query": pagination_query,
        "selected_flight": selected_flight,
        "selected_flight_reason": selected_flight_reason,
        "selected_flight_next_action": selected_flight_next_action,
        "selected_flight_priority": selected_flight_priority,
        "selected_flight_priority_key": selected_flight_priority_key,
        "attention_queue": attention_queue,
        "search_query": q,
        "selected_source": source,
        "selected_status": status,
        **snapshot,
    }

    return render(request, "monitoring/index.html", context)


@login_required
def monitoring_critical_view(request):
    base_flights = get_monitoring_base_queryset()
    snapshot = get_monitoring_snapshot(base_flights)

    selected_status = request.GET.get("status", "").strip().lower()

    critical_source = snapshot.get("critical_flights", Flight.objects.none())
    attention_source = snapshot.get("attention_flights", Flight.objects.none())

    critical_ids = []
    attention_ids = []

    for flight in critical_source:
        if getattr(flight, "pk", None):
            critical_ids.append(flight.pk)

    for flight in attention_source:
        if getattr(flight, "pk", None):
            attention_ids.append(flight.pk)

    critical_queryset = base_flights.filter(pk__in=critical_ids)
    attention_queryset = base_flights.filter(pk__in=attention_ids)

    if selected_status == "cancelled":
        flights = critical_queryset.filter(status="cancelled")

    elif selected_status == "high_risk":
        high_risk_ids = []

        for flight in critical_queryset:
            try:
                profile = compute_operational_profile(flight)
            except (TypeError, ValueError, AttributeError, KeyError):
                continue

            if profile.get("risk_level_key") == "high":
                high_risk_ids.append(flight.pk)

        flights = critical_queryset.filter(pk__in=high_risk_ids)

    elif selected_status == "attention":
        flights = attention_queryset

    elif selected_status == "delayed":
        flights = attention_queryset.filter(status="delayed")

    else:
        flights = critical_queryset

    flights = flights.order_by("-scheduled_departure")

    critical_count = snapshot.get("critical_count", 0)
    attention_count = snapshot.get("attention_count", 0)
    cancelled_count = snapshot.get("cancelled_count", 0)
    delayed_count = snapshot.get("delayed_count", 0)

    if critical_count == 0:
        critical_summary = _("No critical flight currently requires recovery handling.")
    else:
        critical_summary = ngettext(
            "%(count)s critical flight currently requires recovery handling.",
            "%(count)s critical flights currently require recovery handling.",
            critical_count,
        ) % {"count": critical_count}

    context = {
        **snapshot,
        "flights": flights,
        "selected_status": selected_status,
        "critical_count": critical_count,
        "attention_count": attention_count,
        "critical_summary": critical_summary,
        "delayed_count": delayed_count,
        "cancelled_count": cancelled_count,
        "high_risk_count": snapshot.get("high_risk_count", 0),
        "medium_risk_count": snapshot.get("medium_risk_count", 0),
        "disruption_score": snapshot.get("disruption_score", 0),
        "alert_level": snapshot.get("alert_level", "Normal"),
        "alert_level_display": snapshot.get("alert_level_display", _("Normal")),
        "alert_reason": snapshot.get("alert_reason", _("System operating normally")),
        "critical_flights": critical_queryset.order_by("-scheduled_departure")[:8],
        "attention_flights": attention_queryset.order_by("-scheduled_departure")[:8],
    }

    return render(request, "monitoring/critical.html", context)


@login_required
def monitoring_alerts_view(request):
    flights = get_monitoring_base_queryset()
    snapshot = get_monitoring_snapshot(flights)

    alerts = []

    if snapshot["alert_level"] == "High":
        alerts.append(
            {
                "title": _("Critical recovery pressure"),
                "description": _(
                    "Critical recovery pressure is visible across the monitored traffic picture."
                ),
                "level": "high",
                "level_display": _("High"),
            }
        )

    if snapshot["cancelled_count"] > 0:
        count = snapshot["cancelled_count"]

        alerts.append(
            {
                "title": _("Cancelled flights require recovery"),
                "description": ngettext(
                    "%(count)s cancelled flight requires recovery handling.",
                    "%(count)s cancelled flights require recovery handling.",
                    count,
                )
                % {"count": count},
                "level": "high",
                "level_display": _("High"),
            }
        )

    if snapshot.get("critical_count", 0) > 0:
        count = snapshot["critical_count"]

        alerts.append(
            {
                "title": _("Critical flights prioritized"),
                "description": ngettext(
                    "%(count)s flight is classified as critical according to the recovery logic.",
                    "%(count)s flights are classified as critical according to the recovery logic.",
                    count,
                )
                % {"count": count},
                "level": "high",
                "level_display": _("High"),
            }
        )

    if snapshot["delayed_count"] > 0:
        count = snapshot["delayed_count"]

        alerts.append(
            {
                "title": _("Attention-level delay pressure"),
                "description": ngettext(
                    "%(count)s delayed flight should remain under attention monitoring.",
                    "%(count)s delayed flights should remain under attention monitoring.",
                    count,
                )
                % {"count": count},
                "level": "medium",
                "level_display": _("Medium"),
            }
        )

    if snapshot.get("attention_count", 0) > 0:
        count = snapshot["attention_count"]

        alerts.append(
            {
                "title": _("Attention monitoring required"),
                "description": ngettext(
                    "%(count)s flight is currently in attention posture.",
                    "%(count)s flights are currently in attention posture.",
                    count,
                )
                % {"count": count},
                "level": "medium",
                "level_display": _("Medium"),
            }
        )

    if snapshot["api_count"] > snapshot["local_count"]:
        alerts.append(
            {
                "title": _("External source dominance"),
                "description": _(
                    "Monitoring dataset is mostly API-driven. Validate external freshness and consistency."
                ),
                "level": "medium",
                "level_display": _("Medium"),
            }
        )

    if not alerts:
        alerts.append(
            {
                "title": _("No dominant alert signal"),
                "description": _(
                    "The current monitoring dataset does not expose a major operational alert."
                ),
                "level": "normal",
                "level_display": _("Normal"),
            }
        )

    context = {
        **snapshot,
        "alerts": alerts,
    }

    return render(request, "monitoring/alerts.html", context)


@login_required
def monitoring_live_view(request):
    base_flights = get_monitoring_base_queryset()
    live_flights = base_flights.filter(status__in=["boarding", "departed", "in_air"])

    live_count = live_flights.count()
    boarding_count = live_flights.filter(status="boarding").count()
    departed_count = live_flights.filter(status="departed").count()
    in_air_count = live_flights.filter(status="in_air").count()

    api_count = live_flights.filter(source_type="api").count()
    local_count = live_flights.filter(source_type="local").count()

    if live_count == 0:
        live_summary = _(
            "No active flight is currently moving through live execution states."
        )
    else:
        live_summary = ngettext(
            "%(count)s flight is currently moving through live execution states.",
            "%(count)s flights are currently moving through live execution states.",
            live_count,
        ) % {"count": live_count}

    context = {
        "live_flights": live_flights,
        "live_count": live_count,
        "boarding_count": boarding_count,
        "departed_count": departed_count,
        "in_air_count": in_air_count,
        "api_count": api_count,
        "local_count": local_count,
        "live_summary": live_summary,
        "page_title": _("Live Operations"),
        "page_subtitle": _("Flights currently in active operational progression."),
    }

    return render(request, "monitoring/live.html", context)


@login_required
def monitoring_flight_detail_view(request, pk):
    flight = get_object_or_404(
        get_monitoring_base_queryset(),
        pk=pk,
    )

    monitoring_reason = get_flight_monitoring_reason(flight)

    try:
        operational_profile = compute_operational_profile(flight)
        urgency_key = operational_profile["posture"]
    except (TypeError, ValueError, AttributeError, KeyError):
        urgency_key = "normal"

        if flight.status == "cancelled":
            urgency_key = "critical"
        elif flight.status == "delayed":
            urgency_key = "attention"
        elif flight.status in ["boarding", "departed"]:
            urgency_key = "attention"
        elif flight.status == "in_air":
            urgency_key = "active"

    urgency = translate_priority_label(urgency_key)

    history = get_history_summary(flight)
    history_entries = flight.status_history.all().order_by("-changed_at")
    latest_history = history["latest_event"]

    departure_delay_minutes = flight.get_departure_delay_minutes()
    arrival_delay_minutes = flight.get_arrival_delay_minutes()

    progress = get_progress_by_status(flight.status)
    has_live_position = (
        flight.live_latitude is not None
        and flight.live_longitude is not None
    )

    tracking_meta = compute_tracking_confidence(flight)

    risk_score = compute_risk_score(
        flight=flight,
        progress=progress,
        has_live_position=has_live_position,
        tracking_meta=tracking_meta,
        history=history,
    )

    risk_level = get_risk_level(risk_score)
    risk_level_display = translate_risk_level(risk_level)

    current_operational_note = build_operational_recommendation(
        flight=flight,
        risk_level=risk_level,
        remaining_km=0,
        tracking_meta=tracking_meta,
    )

    next_operational_action = build_next_operational_action(
        flight=flight,
        risk_level=risk_level,
        tracking_meta=tracking_meta,
    )

    context = {
        "flight": flight,
        "monitoring_reason": monitoring_reason,
        "urgency": urgency,
        "urgency_key": urgency_key,
        "history_entries": history_entries,
        "latest_history": latest_history,
        "status_change_events": history["status_changes"],
        "disruption_events": history["disruption_events"],
        "schedule_change_events": history_entries.filter(schedule_changed=True).count(),
        "live_update_events": history["live_changes"],
        "departure_delay_minutes": departure_delay_minutes,
        "arrival_delay_minutes": arrival_delay_minutes,
        "current_operational_note": current_operational_note,
        "next_operational_action": next_operational_action,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_level_display": risk_level_display,
        "tracking_meta": tracking_meta,
    }

    return render(request, "monitoring/flight_detail.html", context)


@login_required
def map_view(request):
    flights = (
        get_monitoring_base_queryset()
        .exclude(origin_airport__latitude__isnull=True)
        .exclude(origin_airport__longitude__isnull=True)
        .exclude(destination_airport__latitude__isnull=True)
        .exclude(destination_airport__longitude__isnull=True)
        .exclude(origin_airport__latitude=0)
        .exclude(origin_airport__longitude=0)
        .exclude(destination_airport__latitude=0)
        .exclude(destination_airport__longitude=0)
    )

    selected_flight_id = None
    flight_id = request.GET.get("flight")

    if flight_id and flight_id.isdigit():
        selected_flight_id = int(flight_id)

    context = build_map_context(
        flights=flights,
        selected_flight_id=selected_flight_id,
    )

    context["weather_api_key"] = getattr(settings, "OPENWEATHERMAP_API_KEY", "")

    return render(request, "monitoring/map.html", context)


@login_required
@require_POST
def weather_hazards_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {
                "ok": False,
                "error": "Invalid JSON payload.",
            },
            status=400,
        )

    airports = payload.get("airports", [])
    operational_summary = payload.get("operational_summary", {})

    if not isinstance(airports, list):
        return JsonResponse(
            {
                "ok": False,
                "error": "Airports must be a list.",
            },
            status=400,
        )

    if not isinstance(operational_summary, dict):
        operational_summary = {}

    try:
        result = WeatherHazardService.build_weather_payload(
            airports=airports,
            operational_summary=operational_summary,
        )
    except Exception as exc:
        return JsonResponse(
            {
                "ok": False,
                "error": "Weather hazard service failed.",
                "details": str(exc),
            },
            status=500,
        )

    return JsonResponse(result)