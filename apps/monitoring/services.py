from datetime import timedelta
from math import atan2, cos, radians, sin, sqrt

from django.db.models import Count
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _, ngettext

from apps.flights.models import Flight


SEMI_REAL_MODE = True
SEMI_REAL_STALE_THRESHOLD_MINUTES = 180


def haversine_km(lat1, lon1, lat2, lon2):
    earth_radius_km = 6371.0

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return round(earth_radius_km * c, 1)


def translate_alert_level(level):
    labels = {
        "High": _("High"),
        "Medium": _("Medium"),
        "Normal": _("Normal"),
    }

    return labels.get(level, level)


def translate_priority_label(priority):
    labels = {
        "immediate": _("Immediate"),
        "critical": _("Critical"),
        "high": _("High"),
        "active": _("Active"),
        "attention": _("Attention"),
        "normal": _("Normal"),
        "routine": _("Routine"),
    }

    return labels.get(priority, priority)


def translate_risk_level(risk_level):
    labels = {
        "High Risk": _("High Risk"),
        "Medium Risk": _("Medium Risk"),
        "Low Risk": _("Low Risk"),
    }

    return labels.get(risk_level, risk_level)


def get_source_display(source_type):
    if source_type == "api":
        return _("API")

    if source_type == "local":
        return _("Local")

    return _("Unknown")


def get_progress_by_status(status):
    progress_map = {
        "scheduled": 0.10,
        "boarding": 0.22,
        "departed": 0.42,
        "in_air": 0.68,
        "landed": 1.0,
        "delayed": 0.18,
        "cancelled": 0.0,
    }

    return progress_map.get(status, 0.10)


def get_semi_real_freshness_minutes(flight):
    flight_id = getattr(flight, "id", None) or 1

    try:
        flight_id = int(flight_id)
    except (TypeError, ValueError):
        flight_id = 1

    return 2 + ((flight_id * 7) % 16)


def get_live_freshness_minutes(flight):
    has_live_position = (
        flight.live_latitude is not None
        and flight.live_longitude is not None
    )

    if not flight.updated_at:
        if SEMI_REAL_MODE and has_live_position:
            return get_semi_real_freshness_minutes(flight)

        return None

    delta = timezone.now() - flight.updated_at
    minutes = max(0, int(delta.total_seconds() // 60))

    if SEMI_REAL_MODE and has_live_position and minutes > SEMI_REAL_STALE_THRESHOLD_MINUTES:
        return get_semi_real_freshness_minutes(flight)

    return minutes


def get_operational_updated_at(flight, freshness_minutes):
    if SEMI_REAL_MODE and freshness_minutes is not None:
        return timezone.now() - timedelta(minutes=freshness_minutes)

    return flight.updated_at


def get_history_summary(flight):
    history_qs = flight.status_history.all()

    total_events = history_qs.count()
    disruption_events = history_qs.filter(is_disruption_event=True).count()
    status_changes = history_qs.filter(status_changed=True).count()
    live_changes = history_qs.filter(live_data_changed=True).count()

    latest_event = history_qs.first()

    return {
        "total_events": total_events,
        "disruption_events": disruption_events,
        "status_changes": status_changes,
        "live_changes": live_changes,
        "latest_event": latest_event,
    }


def get_monitoring_base_queryset():
    return (
        Flight.objects.select_related(
            "airline",
            "aircraft",
            "origin_airport",
            "destination_airport",
        )
        .prefetch_related("status_history")
        .order_by("-scheduled_departure")
    )


def compute_operational_profile(flight):
    progress = get_progress_by_status(flight.status)

    has_live_position = (
        flight.live_latitude is not None
        and flight.live_longitude is not None
    )

    tracking_meta = compute_tracking_confidence(flight)
    history = get_history_summary(flight)

    risk_score = compute_risk_score(
        flight=flight,
        progress=progress,
        has_live_position=has_live_position,
        tracking_meta=tracking_meta,
        history=history,
    )

    risk_level = get_risk_level(risk_score)
    risk_level_key = normalize_risk_level_key(risk_level)

    if flight.status == "cancelled" or risk_level_key == "high":
        posture = "critical"
        posture_display = _("Critical")
    elif flight.status == "delayed" or risk_level_key == "medium":
        posture = "attention"
        posture_display = _("Attention")
    else:
        posture = "normal"
        posture_display = _("Normal")

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_level_key": risk_level_key,
        "risk_level_display": translate_risk_level(risk_level),
        "posture": posture,
        "posture_display": posture_display,
        "tracking_meta": tracking_meta,
        "history": history,
    }


def get_monitoring_snapshot(flights):
    total_flights = flights.count()
    scheduled_count = flights.filter(status="scheduled").count()
    boarding_count = flights.filter(status="boarding").count()
    active_count = flights.exclude(status__in=["landed", "cancelled"]).count()
    delayed_count = flights.filter(status="delayed").count()
    cancelled_count = flights.filter(status="cancelled").count()
    in_air_count = flights.filter(status="in_air").count()
    departed_count = flights.filter(status="departed").count()
    landed_count = flights.filter(status="landed").count()

    api_count = flights.filter(source_type="api").count()
    local_count = flights.filter(source_type="local").count()

    delay_rate = round((delayed_count / total_flights) * 100, 1) if total_flights else 0
    cancellation_rate = round((cancelled_count / total_flights) * 100, 1) if total_flights else 0
    active_rate = round((active_count / total_flights) * 100, 1) if total_flights else 0

    busiest_airline = (
        flights.values(
            "airline__id",
            "airline__name",
        )
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    busiest_route = (
        flights.values(
            "origin_airport__iata_code",
            "destination_airport__iata_code",
        )
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    operational_profiles = []
    critical_flight_ids = []
    attention_flight_ids = []
    high_risk_count = 0
    medium_risk_count = 0
    low_risk_count = 0

    for flight in flights:
        try:
            profile = compute_operational_profile(flight)
        except (TypeError, ValueError, AttributeError):
            continue

        operational_profiles.append(
            {
                "flight_id": flight.id,
                "flight": flight,
                **profile,
            }
        )

        if profile["risk_level_key"] == "high":
            high_risk_count += 1
        elif profile["risk_level_key"] == "medium":
            medium_risk_count += 1
        else:
            low_risk_count += 1

        if profile["posture"] == "critical":
            critical_flight_ids.append(flight.id)

        if profile["posture"] == "attention":
            attention_flight_ids.append(flight.id)

    critical_count = len(critical_flight_ids)
    attention_count = len(attention_flight_ids)

    critical_flights = flights.filter(pk__in=critical_flight_ids).order_by("-scheduled_departure")[:8]
    attention_flights = flights.filter(pk__in=attention_flight_ids).order_by("-scheduled_departure")[:8]

    disruption_score = (
        (cancelled_count * 15)
        + (delayed_count * 4)
        + (high_risk_count * 8)
        + (medium_risk_count * 2)
    )

    disruption_score = min(disruption_score, 100)

    alert_level = "Normal"
    alert_reason = _("System operating normally")

    if critical_count >= 4 or cancelled_count >= 3 or disruption_score >= 80:
        alert_level = "High"
        alert_reason = _("Critical recovery pressure detected")
    elif attention_count >= 3 or delayed_count >= 2 or disruption_score >= 32:
        alert_level = "Medium"
        alert_reason = _("Moderate disruption or attention pressure detected")

    alert_level_display = translate_alert_level(alert_level)

    monitoring_mode_key = "stable"
    monitoring_mode = _("Stable Operations")

    if alert_level == "High":
        monitoring_mode_key = "critical"
        monitoring_mode = _("Critical Supervision")
    elif alert_level == "Medium":
        monitoring_mode_key = "elevated"
        monitoring_mode = _("Elevated Supervision")

    recommendations = []

    if cancelled_count > 0:
        recommendations.append(
            ngettext(
                "%(count)s cancelled flight requires recovery review.",
                "%(count)s cancelled flights require recovery review.",
                cancelled_count,
            ) % {"count": cancelled_count}
        )

    if delayed_count > 0:
        recommendations.append(
            ngettext(
                "%(count)s delayed flight should remain under attention monitoring.",
                "%(count)s delayed flights should remain under attention monitoring.",
                delayed_count,
            ) % {"count": delayed_count}
        )

    if critical_count > 0:
        recommendations.append(
            ngettext(
                "%(count)s critical flight is currently prioritized for operational review.",
                "%(count)s critical flights are currently prioritized for operational review.",
                critical_count,
            ) % {"count": critical_count}
        )

    if busiest_airline:
        recommendations.append(
            _("%(airline)s is currently the most active airline and should be monitored closely.")
            % {"airline": busiest_airline["airline__name"]}
        )

    if busiest_route:
        origin = busiest_route["origin_airport__iata_code"] or "---"
        destination = busiest_route["destination_airport__iata_code"] or "---"

        recommendations.append(
            _("The busiest route is %(route)s. Consider route-level performance tracking.")
            % {"route": f"{origin} → {destination}"}
        )

    if api_count > local_count:
        recommendations.append(
            _("API-synchronized flights dominate the monitoring dataset. Validate external data freshness regularly.")
        )
    else:
        recommendations.append(
            _("Local flights remain significant in the monitoring dataset. Keep manual operational updates consistent.")
        )

    if in_air_count > scheduled_count:
        recommendations.append(
            _("Live operational activity exceeds waiting departures. Focus on airborne supervision and arrival coordination.")
        )

    return {
        "total_flights": total_flights,
        "scheduled_count": scheduled_count,
        "boarding_count": boarding_count,
        "active_count": active_count,
        "delayed_count": delayed_count,
        "cancelled_count": cancelled_count,
        "in_air_count": in_air_count,
        "departed_count": departed_count,
        "landed_count": landed_count,
        "api_count": api_count,
        "local_count": local_count,
        "delay_rate": delay_rate,
        "cancellation_rate": cancellation_rate,
        "active_rate": active_rate,
        "busiest_airline": busiest_airline,
        "busiest_route": busiest_route,
        "critical_count": critical_count,
        "attention_count": attention_count,
        "high_risk_count": high_risk_count,
        "medium_risk_count": medium_risk_count,
        "low_risk_count": low_risk_count,
        "critical_flights": critical_flights,
        "attention_flights": attention_flights,
        "operational_profiles": operational_profiles,
        "alert_level": alert_level,
        "alert_level_display": alert_level_display,
        "alert_reason": alert_reason,
        "monitoring_mode": monitoring_mode,
        "monitoring_mode_key": monitoring_mode_key,
        "disruption_score": disruption_score,
        "recommendations": recommendations,
    }


def get_flight_monitoring_reason(flight):
    if flight.status == "cancelled":
        return _("Flight cancelled. Immediate disruption review required.")

    if flight.status == "delayed":
        return _("Flight delayed. Check turnaround, route congestion, and downstream impact.")

    if flight.status == "in_air":
        return _("Flight currently active in airspace and under live supervision.")

    if flight.status == "boarding":
        return _("Boarding in progress. Departure readiness should be monitored.")

    if flight.status == "departed":
        return _("Departure confirmed. Track progression toward stable airborne state.")

    if flight.status == "landed":
        return _("Flight completed. Keep for traceability and post-operation analysis.")

    return _("Standard monitoring state.")


def get_attention_label(flight):
    if flight.status == "cancelled":
        return _("Immediate Action")

    if flight.status == "delayed":
        return _("Attention Review")

    if flight.status == "in_air":
        return _("Live Tracking")

    if flight.status in ["boarding", "departed"]:
        return _("Departure Control")

    return _("Routine Check")


def get_attention_priority(flight):
    try:
        profile = compute_operational_profile(flight)
    except (TypeError, ValueError, AttributeError):
        profile = None

    if profile and profile["posture"] == "critical":
        return 100

    if flight.status == "cancelled":
        return 95

    if profile and profile["posture"] == "attention":
        return 75

    if flight.status == "delayed":
        return 70

    if flight.status == "in_air":
        return 55

    if flight.status == "boarding":
        return 45

    if flight.status == "departed":
        return 40

    if flight.status == "scheduled":
        return 20

    return 10


def build_attention_queue(flights, limit=6):
    queue = []

    for flight in flights:
        reason = get_flight_monitoring_reason(flight)
        attention_label = get_attention_label(flight)
        priority = get_attention_priority(flight)

        queue.append(
            {
                "flight": flight,
                "reason": reason,
                "attention_label": attention_label,
                "priority": priority,
            }
        )

    queue.sort(
        key=lambda item: (
            -item["priority"],
            item["flight"].scheduled_departure if item["flight"].scheduled_departure else timezone.now(),
        )
    )

    return queue[:limit]


def compute_tracking_confidence(flight):
    has_live_position = (
        flight.live_latitude is not None
        and flight.live_longitude is not None
    )

    if not has_live_position:
        return {
            "tracking_label": _("Estimated"),
            "tracking_confidence": "estimated",
            "tracking_confidence_score": 0,
            "tracking_posture": _("Estimated route continuity"),
            "tracking_mode": _("Estimated"),
            "tracking_mode_key": "estimated",
            "position_source_label": _("Interpolated route progression"),
            "position_source_detail": _("No live coordinates available. Position is estimated from route progression."),
            "is_live_confirmed": False,
            "is_live_low_confidence": False,
            "is_live_associated": False,
            "live_freshness_minutes": None,
        }

    freshness_minutes = get_live_freshness_minutes(flight)

    if flight.external_id and flight.source_type == "api":
        return {
            "tracking_label": _("Live Confirmed"),
            "tracking_confidence": "high",
            "tracking_confidence_score": 100,
            "tracking_posture": _("Trusted live tracking"),
            "tracking_mode": _("Live"),
            "tracking_mode_key": "live",
            "position_source_label": _("External live feed"),
            "position_source_detail": _("Live coordinates matched through strong external association."),
            "is_live_confirmed": True,
            "is_live_low_confidence": False,
            "is_live_associated": False,
            "live_freshness_minutes": freshness_minutes,
        }

    if flight.external_id:
        return {
            "tracking_label": _("Live Associated"),
            "tracking_confidence": "medium",
            "tracking_confidence_score": 70,
            "tracking_posture": _("Associated live tracking"),
            "tracking_mode": _("Live"),
            "tracking_mode_key": "live",
            "position_source_label": _("Associated live feed"),
            "position_source_detail": _("Live coordinates are associated to the flight, but not with the strongest identification level."),
            "is_live_confirmed": False,
            "is_live_low_confidence": False,
            "is_live_associated": True,
            "live_freshness_minutes": freshness_minutes,
        }

    return {
        "tracking_label": _("Live Low Confidence"),
        "tracking_confidence": "low",
        "tracking_confidence_score": 35,
        "tracking_posture": _("Validate before escalation"),
        "tracking_mode": _("Live"),
        "tracking_mode_key": "live",
        "position_source_label": _("Low-confidence live association"),
        "position_source_detail": _("Live coordinates exist, but flight identity should be validated before strong operational decisions."),
        "is_live_confirmed": False,
        "is_live_low_confidence": True,
        "is_live_associated": False,
        "live_freshness_minutes": freshness_minutes,
    }


def compute_risk_score(flight, progress, has_live_position, tracking_meta, history):
    score = 6

    status_weights = {
        "scheduled": 2,
        "boarding": 8,
        "departed": 12,
        "in_air": 18,
        "landed": 1,
        "delayed": 42,
        "cancelled": 70,
    }

    score += status_weights.get(flight.status, 4)

    if flight.source_type == "api":
        score += 2
    else:
        score += 1

    if not has_live_position:
        score += 5

    if tracking_meta["tracking_confidence"] == "low":
        score += 8
    elif tracking_meta["tracking_confidence"] == "estimated":
        score += 5
    elif tracking_meta["tracking_confidence"] == "medium":
        score += 3

    progress_percent = round(progress * 100)

    if progress_percent >= 50:
        score += 3

    if progress_percent >= 80:
        score += 4

    departure_delay = flight.get_departure_delay_minutes()
    arrival_delay = flight.get_arrival_delay_minutes()

    if departure_delay is not None:
        if departure_delay >= 90:
            score += 16
        elif departure_delay >= 45:
            score += 10
        elif departure_delay >= 15:
            score += 5

    if arrival_delay is not None:
        if arrival_delay >= 90:
            score += 12
        elif arrival_delay >= 45:
            score += 8
        elif arrival_delay >= 15:
            score += 4

    if flight.live_speed is not None:
        speed = float(flight.live_speed)

        if flight.status in ["departed", "in_air"]:
            if speed < 220:
                score += 6
            elif speed < 450:
                score += 3

    if flight.live_altitude is not None:
        altitude = float(flight.live_altitude)

        if flight.status in ["departed", "in_air"] and altitude < 3000:
            score += 5

    freshness_minutes = tracking_meta.get("live_freshness_minutes")

    if freshness_minutes is not None:
        if freshness_minutes > 120:
            score += 5
        elif freshness_minutes > 60:
            score += 2

    if history["disruption_events"] >= 3:
        score += 6
    elif history["disruption_events"] >= 1:
        score += 3

    if history["status_changes"] >= 4:
        score += 3

    return min(score, 100)


def get_risk_level(score):
    if score >= 82:
        return "High Risk"

    if score >= 45:
        return "Medium Risk"

    return "Low Risk"


def get_route_alert(flight, risk_level, tracking_meta):
    if flight.status == "cancelled":
        return _("Critical Corridor")

    if flight.status == "delayed":
        return _("Disrupted Corridor")

    if tracking_meta["tracking_confidence"] == "low" and risk_level == "High Risk":
        return _("Sensitive Corridor")

    if risk_level == "High Risk":
        return _("Sensitive Corridor")

    if flight.status == "in_air":
        return _("Active Corridor")

    if flight.status in ["boarding", "departed"]:
        return _("Monitored Corridor")

    return _("Normal Corridor")


def estimate_eta(flight, remaining_km, progress):
    if flight.status == "cancelled":
        return None

    if flight.status == "landed":
        return flight.actual_arrival or flight.scheduled_arrival

    if flight.live_speed and float(flight.live_speed) > 0:
        hours_left = remaining_km / float(flight.live_speed)
        return timezone.now() + timedelta(hours=hours_left)

    scheduled_duration_hours = None

    if flight.scheduled_departure and flight.scheduled_arrival:
        duration_seconds = (flight.scheduled_arrival - flight.scheduled_departure).total_seconds()

        if duration_seconds > 0:
            scheduled_duration_hours = duration_seconds / 3600

    if scheduled_duration_hours:
        remaining_ratio = max(0, 1 - progress)
        estimated_hours_left = scheduled_duration_hours * remaining_ratio
        return timezone.now() + timedelta(hours=estimated_hours_left)

    return flight.scheduled_arrival


def build_next_operational_action(flight, risk_level, tracking_meta):
    if flight.status == "cancelled":
        return _("Escalate to recovery handling and disruption review.")

    if flight.status == "delayed":
        return _("Keep under attention monitoring and review delay propagation.")

    if tracking_meta["tracking_confidence"] == "low":
        return _("Validate aircraft identity before relying on live position for strong escalation.")

    if flight.status == "in_air" and risk_level == "High Risk":
        return _("Maintain close live supervision until arrival.")

    if flight.status == "in_air":
        return _("Track arrival readiness and route progression.")

    if flight.status == "boarding":
        return _("Verify departure readiness.")

    if flight.status == "departed":
        return _("Confirm transition to stable in-air state.")

    if flight.status == "landed":
        return _("Archive for traceability and analytics.")

    return _("Continue routine monitoring.")


def build_operational_recommendation(flight, risk_level, remaining_km, tracking_meta):
    delay_departure = flight.get_departure_delay_minutes()
    delay_arrival = flight.get_arrival_delay_minutes()

    if flight.status == "cancelled":
        return _(
            "Recovery handling required. Confirm disruption scope, re-evaluate corridor continuity, "
            "and route this flight into the recovery workflow."
        )

    if flight.status == "delayed":
        if delay_departure is not None and delay_departure >= 45:
            return _(
                "Strong delay pressure detected with about %(minutes)s minutes of departure deviation. "
                "Prioritize route review, turnaround validation, and downstream schedule impact."
            ) % {"minutes": delay_departure}

        return _(
            "Delay pressure detected. Keep the flight under attention monitoring, verify turnaround causes, "
            "and anticipate propagation impact on connected operations."
        )

    if tracking_meta["tracking_confidence"] == "low":
        return _(
            "Live position is associated with low confidence. Keep the route visible, "
            "but validate aircraft identity before taking strong operational decisions."
        )

    if flight.status == "in_air" and risk_level == "High Risk":
        return _(
            "Flight is airborne with elevated sensitivity and about %(remaining_km)s km remaining. "
            "Maintain close supervision, monitor approach stability, and prepare arrival coordination."
        ) % {"remaining_km": remaining_km}

    if flight.status == "in_air":
        return _(
            "Flight is airborne with about %(remaining_km)s km remaining. "
            "Continue route supervision and prepare arrival-side coordination."
        ) % {"remaining_km": remaining_km}

    if flight.status == "boarding":
        return _(
            "Boarding is active. Verify whether the flight can convert to departure on schedule "
            "and watch for early operational drift."
        )

    if flight.status == "departed":
        return _(
            "Departure confirmed. Track early route progression until the flight reaches a stable in-air profile."
        )

    if flight.status == "landed":
        if delay_arrival is not None and delay_arrival > 0:
            return _(
                "Flight has landed with about %(minutes)s minutes of arrival deviation. "
                "Keep this record for post-operation review and performance interpretation."
            ) % {"minutes": delay_arrival}

        return _("Flight completed normally. Preserve this record for traceability and historical analytics.")

    return _("Low immediate operational pressure. Continue routine monitoring and data consistency checks.")


def build_action_engine(flight, risk_level, tracking_meta, remaining_km, eta):
    status = flight.status
    departure_delay = flight.get_departure_delay_minutes()
    arrival_delay = flight.get_arrival_delay_minutes()

    action_required = _("Continue routine monitoring.")
    action_priority = _("Routine")
    action_priority_key = "routine"
    impact_level = _("Low Operational Impact")
    decision_deadline = _("Next routine review")
    supervision_window = _("Standard monitoring window")
    command_tag = _("Observe")

    if status == "cancelled":
        action_required = _("Escalate cancellation, isolate disruption scope, and coordinate downstream recovery actions.")
        action_priority = _("Immediate")
        action_priority_key = "immediate"
        impact_level = _("Network Disruption Risk")
        decision_deadline = _("Now")
        supervision_window = _("Recovery supervision until disruption is contained")
        command_tag = _("Recover")

    elif status == "delayed":
        if departure_delay is not None and departure_delay >= 45:
            action_required = _("Review turnaround blockage, route pressure, and recovery sequencing before further propagation.")
            action_priority = _("Attention")
            action_priority_key = "attention"
            impact_level = _("Departure Wave Pressure")
            decision_deadline = _("Within 15 minutes")
            supervision_window = _("Tight attention cycle until departure stability is restored")
            command_tag = _("Stabilize")
        else:
            action_required = _("Validate delay source, monitor propagation, and prepare recovery if schedule pressure increases.")
            action_priority = _("Attention")
            action_priority_key = "attention"
            impact_level = _("Moderate Schedule Impact")
            decision_deadline = _("Within 30 minutes")
            supervision_window = _("Short attention cycle")
            command_tag = _("Monitor")

    elif tracking_meta["tracking_confidence"] == "low":
        action_required = _("Validate aircraft identity before using this live position for strong operational escalation.")
        action_priority = _("Attention")
        action_priority_key = "attention"
        impact_level = _("Tracking Reliability Risk")
        decision_deadline = _("Before next escalation")
        supervision_window = _("Identity validation window")
        command_tag = _("Validate")

    elif status == "in_air" and risk_level == "High Risk":
        eta_text = eta.strftime("%H:%M") if eta else _("unknown ETA")
        action_required = _(
            "Maintain close en-route supervision, monitor approach stability, and prepare arrival coordination before %(eta)s."
        ) % {"eta": eta_text}
        action_priority = _("Immediate")
        action_priority_key = "immediate"
        impact_level = _("Arrival Coordination Risk")
        decision_deadline = _("Before approach phase")
        supervision_window = _("Continuous until landing")
        command_tag = _("Control")

    elif status == "in_air" and risk_level == "Medium Risk":
        action_required = _(
            "Track route progression and prepare arrival-side coordination with about %(remaining_km)s km remaining."
        ) % {"remaining_km": remaining_km}
        action_priority = _("Attention")
        action_priority_key = "attention"
        impact_level = _("Moderate Arrival Pressure")
        decision_deadline = _("Before arrival sequence")
        supervision_window = _("Active flight supervision window")
        command_tag = _("Monitor")

    elif status == "in_air":
        action_required = _(
            "Maintain route supervision and prepare normal arrival handling with about %(remaining_km)s km remaining."
        ) % {"remaining_km": remaining_km}
        action_priority = _("Attention")
        action_priority_key = "attention"
        impact_level = _("Contained Operational Impact")
        decision_deadline = _("Before arrival")
        supervision_window = _("Active monitoring window")
        command_tag = _("Track")

    elif status == "boarding":
        action_required = _("Verify departure readiness and detect early drift before pushback execution.")
        action_priority = _("Attention")
        action_priority_key = "attention"
        impact_level = _("Gate-to-departure Risk")
        decision_deadline = _("Before departure release")
        supervision_window = _("Pre-departure control window")
        command_tag = _("Prepare")

    elif status == "departed":
        action_required = _("Confirm clean transition into stable airborne state and monitor initial route execution.")
        action_priority = _("Attention")
        action_priority_key = "attention"
        impact_level = _("Early Flight Stability Risk")
        decision_deadline = _("Within next control cycle")
        supervision_window = _("Initial climb and route stabilization window")
        command_tag = _("Confirm")

    elif status == "landed":
        if arrival_delay is not None and arrival_delay > 0:
            action_required = _("Close operation, register arrival deviation, and preserve traceability for performance review.")
            action_priority = _("Routine")
            action_priority_key = "routine"
            impact_level = _("Post-operation Deviation")
            decision_deadline = _("Before archival review")
            supervision_window = _("Post-arrival analysis window")
            command_tag = _("Archive")
        else:
            action_required = _("Close supervision cycle and preserve operation data for analytics.")
            action_priority = _("Routine")
            action_priority_key = "routine"
            impact_level = _("Low Operational Impact")
            decision_deadline = _("Standard closure")
            supervision_window = _("Archive window")
            command_tag = _("Close")

    if risk_level == "High Risk" and action_priority_key != "immediate":
        action_priority = _("High")
        action_priority_key = "high"

    return {
        "action_required": action_required,
        "action_priority": action_priority,
        "action_priority_key": action_priority_key,
        "impact_level": impact_level,
        "decision_deadline": decision_deadline,
        "supervision_window": supervision_window,
        "command_tag": command_tag,
    }


def compute_map_priority(risk_score, risk_level, flight, tracking_meta, history):
    score = 0

    if risk_level == "High Risk":
        score += 100
    elif risk_level == "Medium Risk":
        score += 45
    else:
        score += 15

    if flight.status == "cancelled":
        score += 80
    elif flight.status == "delayed":
        score += 45
    elif flight.status == "in_air":
        score += 15
    elif flight.status in ["boarding", "departed"]:
        score += 8

    if tracking_meta["tracking_confidence"] == "high":
        score += 12
    elif tracking_meta["tracking_confidence"] == "medium":
        score += 8
    elif tracking_meta["tracking_confidence"] == "low":
        score += 6
    else:
        score += 2

    freshness_minutes = tracking_meta.get("live_freshness_minutes")

    if freshness_minutes is not None:
        if freshness_minutes <= 10:
            score += 5
        elif freshness_minutes <= 30:
            score += 3
        elif freshness_minutes <= 60:
            score += 1

    if flight.source_type == "api":
        score += 3

    if history["disruption_events"] >= 3:
        score += 5
    elif history["disruption_events"] >= 1:
        score += 2

    score = min(score, 180)

    if flight.status == "cancelled" or risk_level == "High Risk":
        priority_label = _("Critical")
        priority_class = "critical"
    elif flight.status == "delayed" or risk_level == "Medium Risk":
        priority_label = _("Elevated")
        priority_class = "elevated"
    else:
        priority_label = _("Standard")
        priority_class = "standard"

    is_map_critical = priority_class == "critical"
    should_promote_on_map = priority_class in ["critical", "elevated"]
    should_show_label_by_default = is_map_critical or flight.status in ["delayed", "cancelled"]

    return {
        "map_priority_score": score,
        "map_priority_label": priority_label,
        "map_priority_class": priority_class,
        "is_map_critical": is_map_critical,
        "should_promote_on_map": should_promote_on_map,
        "should_show_label_by_default": should_show_label_by_default,
    }


def compute_flight_disruption_score(flight, risk_score, risk_level_key, tracking_meta):
    score = 0

    if flight.status == "cancelled":
        score += 25
    elif flight.status == "delayed":
        score += 14
    elif flight.status == "in_air":
        score += 1

    if risk_level_key == "high":
        score += 10
    elif risk_level_key == "medium":
        score += 4

    if tracking_meta.get("is_live_low_confidence"):
        score += 3

    if risk_score >= 90:
        score += 6
    elif risk_score >= 75:
        score += 3

    return min(score, 40)


def compute_map_supervision_meta(flights_list):
    total_mapped = len(flights_list)
    delayed_count = sum(1 for item in flights_list if item.get("status") == "delayed")
    cancelled_count = sum(1 for item in flights_list if item.get("status") == "cancelled")
    in_air_count = sum(1 for item in flights_list if item.get("status") == "in_air")

    high_risk_count = sum(
        1
        for item in flights_list
        if item.get("risk_level") == "high"
        or item.get("risk_level_display") == "High Risk"
    )

    medium_risk_count = sum(
        1
        for item in flights_list
        if item.get("risk_level") == "medium"
        or item.get("risk_level_display") == "Medium Risk"
    )

    low_confidence_live_count = sum(
        1
        for item in flights_list
        if item.get("is_live_low_confidence")
    )

    critical_count = sum(
        1
        for item in flights_list
        if item.get("status") == "cancelled"
        or item.get("risk_level") == "high"
        or item.get("risk_level_display") == "High Risk"
    )

    attention_count = sum(
        1
        for item in flights_list
        if item.get("status") == "delayed"
        or item.get("risk_level") == "medium"
        or item.get("risk_level_display") == "Medium Risk"
    )

    disruption_score = sum(item.get("disruption_score", 0) or 0 for item in flights_list)

    supervision_mode = _("Stable Operations")
    supervision_mode_key = "stable"
    supervision_reason = _("No major disruption currently detected on the mapped traffic.")

    if disruption_score >= 80 or cancelled_count >= 3 or critical_count >= 4:
        supervision_mode = _("Crisis Supervision")
        supervision_mode_key = "crisis"
        supervision_reason = _(
            "%(cancelled)s cancelled, %(delayed)s delayed, %(critical)s critical flight(s). "
            "Immediate operational coordination required."
        ) % {
            "cancelled": cancelled_count,
            "delayed": delayed_count,
            "critical": critical_count,
        }

    elif disruption_score >= 32 or delayed_count >= 3 or attention_count >= 3:
        supervision_mode = _("Elevated Supervision")
        supervision_mode_key = "elevated"
        supervision_reason = _(
            "%(delayed)s delayed and %(attention)s attention-level flight(s) are increasing operational pressure."
        ) % {
            "delayed": delayed_count,
            "attention": attention_count,
        }

    return {
        "map_total_mapped": total_mapped,
        "map_delayed_count": delayed_count,
        "map_cancelled_count": cancelled_count,
        "map_in_air_count": in_air_count,
        "map_high_risk_count": high_risk_count,
        "map_medium_risk_count": medium_risk_count,
        "map_low_confidence_live_count": low_confidence_live_count,
        "map_critical_count": critical_count,
        "map_attention_count": attention_count,
        "map_disruption_score": disruption_score,
        "map_supervision_mode": supervision_mode,
        "map_supervision_mode_key": supervision_mode_key,
        "map_supervision_reason": supervision_reason,
    }


def get_airport_code(airport):
    if not airport:
        return "N/A"

    for attr in ["iata_code", "icao_code", "code"]:
        value = getattr(airport, attr, None)

        if value:
            return str(value).strip().upper()

    return "N/A"


def get_airport_name(airport):
    if not airport:
        return _("Airport unavailable")

    return (
        getattr(airport, "name", None)
        or getattr(airport, "airport_name", None)
        or get_airport_code(airport)
    )


def get_aircraft_display(aircraft):
    if not aircraft:
        return _("Not assigned")

    for attr in ["model", "aircraft_type", "type", "registration"]:
        value = getattr(aircraft, attr, None)

        if value:
            return str(value)

    return str(aircraft)


def get_aircraft_registration(aircraft):
    if not aircraft:
        return ""

    for attr in ["registration", "registration_number", "tail_number"]:
        value = getattr(aircraft, attr, None)

        if value:
            return str(value)

    return ""


def normalize_route_alert_key(route_alert):
    value = str(route_alert or "").strip().lower()

    if "critical" in value:
        return "critical"

    if "disrupted" in value:
        return "operational"

    if "sensitive" in value:
        return "attention"

    if "active" in value:
        return "attention"

    if "monitored" in value:
        return "attention"

    return "clear"


def normalize_risk_level_key(risk_level):
    value = str(risk_level or "").strip().lower()

    if "high" in value:
        return "high"

    if "medium" in value:
        return "medium"

    return "low"


def build_map_flight_payload(flight):
    progress_ratio = get_progress_by_status(flight.status)
    progress_percent = round(progress_ratio * 100)

    origin_lat = float(flight.origin_airport.latitude)
    origin_lng = float(flight.origin_airport.longitude)
    destination_lat = float(flight.destination_airport.latitude)
    destination_lng = float(flight.destination_airport.longitude)

    has_live_position = (
        flight.live_latitude is not None
        and flight.live_longitude is not None
    )

    total_distance_km = haversine_km(
        origin_lat,
        origin_lng,
        destination_lat,
        destination_lng,
    )

    remaining_distance_km = round(total_distance_km * max(0, 1 - progress_ratio), 1)

    tracking_meta = compute_tracking_confidence(flight)
    history = get_history_summary(flight)

    risk_score = compute_risk_score(
        flight=flight,
        progress=progress_ratio,
        has_live_position=has_live_position,
        tracking_meta=tracking_meta,
        history=history,
    )

    risk_level = get_risk_level(risk_score)
    risk_level_display = translate_risk_level(risk_level)
    risk_level_key = normalize_risk_level_key(risk_level)

    route_alert = get_route_alert(flight, risk_level, tracking_meta)
    route_alert_key = normalize_route_alert_key(route_alert)

    eta = estimate_eta(flight, remaining_distance_km, progress_ratio)

    recommendation = build_operational_recommendation(
        flight=flight,
        risk_level=risk_level,
        remaining_km=remaining_distance_km,
        tracking_meta=tracking_meta,
    )

    next_action = build_next_operational_action(
        flight=flight,
        risk_level=risk_level,
        tracking_meta=tracking_meta,
    )

    action_engine = build_action_engine(
        flight=flight,
        risk_level=risk_level,
        tracking_meta=tracking_meta,
        remaining_km=remaining_distance_km,
        eta=eta,
    )

    map_priority = compute_map_priority(
        risk_score=risk_score,
        risk_level=risk_level,
        flight=flight,
        tracking_meta=tracking_meta,
        history=history,
    )

    departure_delay = flight.get_departure_delay_minutes()
    arrival_delay = flight.get_arrival_delay_minutes()

    monitoring_url = f"{reverse('monitoring:monitoring_home')}?flight={flight.id}"
    detail_url = reverse("flights:flight_detail", args=[flight.id])
    monitoring_detail_url = reverse("monitoring:monitoring_flight_detail", args=[flight.id])

    if flight.source_type == "api":
        source_label = _("API")
        source_detail = _("External synchronized record")
    else:
        source_label = _("Local")
        source_detail = _("Manually maintained local record")

    origin_code = get_airport_code(flight.origin_airport)
    destination_code = get_airport_code(flight.destination_airport)
    origin_name = get_airport_name(flight.origin_airport)
    destination_name = get_airport_name(flight.destination_airport)

    aircraft_display = get_aircraft_display(flight.aircraft)
    aircraft_registration = get_aircraft_registration(flight.aircraft)

    live_lat = float(flight.live_latitude) if flight.live_latitude is not None else None
    live_lng = float(flight.live_longitude) if flight.live_longitude is not None else None

    operational_updated_at = get_operational_updated_at(
        flight=flight,
        freshness_minutes=tracking_meta.get("live_freshness_minutes"),
    )

    updated_at = operational_updated_at.isoformat() if operational_updated_at else None
    updated_at_unix = int(operational_updated_at.timestamp()) if operational_updated_at else None
    actual_updated_at = flight.updated_at.isoformat() if flight.updated_at else None

    eta_display = eta.strftime("%Y-%m-%d %H:%M UTC") if eta else _("ETA unavailable")

    flight_disruption_score = compute_flight_disruption_score(
        flight=flight,
        risk_score=risk_score,
        risk_level_key=risk_level_key,
        tracking_meta=tracking_meta,
    )

    return {
        "id": flight.id,
        "flight_id": flight.id,
        "flight_number": flight.flight_number,
        "callsign": flight.flight_number,

        "airline": flight.airline.name if flight.airline else _("Unknown"),
        "airline_name": flight.airline.name if flight.airline else _("Unknown airline"),

        "aircraft": aircraft_display,
        "aircraft_type": aircraft_display,
        "aircraft_registration": aircraft_registration,

        "status": flight.status,
        "status_display": flight.get_status_display(),

        "source_type": flight.source_type,
        "source": source_label,
        "source_label": source_label,
        "source_detail": source_detail,

        "origin_code": origin_code,
        "destination_code": destination_code,
        "origin_airport_code": origin_code,
        "destination_airport_code": destination_code,
        "departure_airport_code": origin_code,
        "arrival_airport_code": destination_code,
        "departure_iata": origin_code,
        "arrival_iata": destination_code,

        "origin_name": origin_name,
        "destination_name": destination_name,
        "departure_airport_name": origin_name,
        "arrival_airport_name": destination_name,

        "origin_lat": origin_lat,
        "origin_lng": origin_lng,
        "origin_lon": origin_lng,
        "destination_lat": destination_lat,
        "destination_lng": destination_lng,
        "destination_lon": destination_lng,

        "live_lat": live_lat,
        "live_lng": live_lng,
        "live_lon": live_lng,
        "latitude": live_lat,
        "longitude": live_lng,

        "heading": float(flight.live_direction) if flight.live_direction is not None else None,
        "altitude": float(flight.live_altitude) if flight.live_altitude is not None else None,
        "speed": float(flight.live_speed) if flight.live_speed is not None else None,

        "progress": progress_percent,
        "progress_percent": progress_percent,
        "progress_ratio": progress_ratio,

        "total_distance": total_distance_km,
        "total_distance_km": total_distance_km,
        "remaining_distance": remaining_distance_km,
        "remaining_distance_km": remaining_distance_km,
        "distance_remaining_km": remaining_distance_km,

        "eta": eta_display,
        "estimated_arrival": eta_display,
        "arrival_estimate": eta_display,

        "risk_score": risk_score,
        "operational_risk_score": risk_score,
        "risk_level": risk_level_key,
        "risk_level_display": risk_level_display,

        "route_alert": route_alert_key,
        "route_alert_display": route_alert,
        "route_exposure": route_alert_key,
        "alert_level": route_alert_key,

        "priority": action_engine["action_priority_key"],
        "operational_priority": action_engine["action_priority_key"],
        "priority_display": action_engine["action_priority"],

        "disruption_score": flight_disruption_score,
        "impact_score": flight_disruption_score,
        "map_priority_score": map_priority["map_priority_score"],

        "tracking_mode": tracking_meta["tracking_mode_key"],
        "tracking": tracking_meta["tracking_mode_key"],
        "tracking_label": tracking_meta["tracking_label"],
        "tracking_confidence": tracking_meta["tracking_confidence"],
        "tracking_confidence_score": tracking_meta["tracking_confidence_score"],
        "position_source_label": tracking_meta["position_source_label"],
        "position_source_detail": tracking_meta["position_source_detail"],
        "is_live_confirmed": tracking_meta["is_live_confirmed"],
        "is_live_low_confidence": tracking_meta["is_live_low_confidence"],
        "is_live_associated": tracking_meta["is_live_associated"],

        "recommendation": recommendation,
        "next_action": next_action,
        "action_required": action_engine["action_required"],
        "impact_level": action_engine["impact_level"],
        "decision_deadline": action_engine["decision_deadline"],
        "supervision_window": action_engine["supervision_window"],
        "command_tag": action_engine["command_tag"],

        "departure_delay_minutes": departure_delay,
        "arrival_delay_minutes": arrival_delay,

        "updated_at": updated_at,
        "updated_at_unix": updated_at_unix,
        "actual_updated_at": actual_updated_at,
        "last_seen_at": updated_at,
        "last_seen_unix": updated_at_unix,
        "last_position_at": updated_at,

        "detail_url": detail_url,
        "monitoring_url": monitoring_url,
        "monitoring_detail_url": monitoring_detail_url,

        **map_priority,
    }


def build_map_context(flights, selected_flight_id=None):
    mapped_flights = []

    for flight in flights:
        try:
            mapped_flights.append(build_map_flight_payload(flight))
        except (TypeError, ValueError, AttributeError):
            continue

    supervision_meta = compute_map_supervision_meta(mapped_flights)
    selected_flight_id = str(selected_flight_id) if selected_flight_id else ""

    return {
        "map_flights": mapped_flights,
        "map_flights_json": mapped_flights,
        "flights_json": mapped_flights,

        "selected_flight_id": selected_flight_id,

        "map_total_mapped": supervision_meta["map_total_mapped"],
        "map_delayed_count": supervision_meta["map_delayed_count"],
        "map_cancelled_count": supervision_meta["map_cancelled_count"],
        "map_in_air_count": supervision_meta["map_in_air_count"],
        "map_high_risk_count": supervision_meta["map_high_risk_count"],
        "map_medium_risk_count": supervision_meta["map_medium_risk_count"],
        "map_low_confidence_live_count": supervision_meta["map_low_confidence_live_count"],
        "map_critical_count": supervision_meta["map_critical_count"],
        "map_attention_count": supervision_meta["map_attention_count"],
        "map_disruption_score": supervision_meta["map_disruption_score"],
        "map_supervision_mode": supervision_meta["map_supervision_mode"],
        "map_supervision_mode_key": supervision_meta["map_supervision_mode_key"],
        "map_supervision_reason": supervision_meta["map_supervision_reason"],
    }