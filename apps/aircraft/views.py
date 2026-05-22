from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, render

from .models import Aircraft
from apps.flights.models import Flight


ACTIVE_FLIGHT_STATUSES = ["scheduled", "boarding", "departed", "in_air", "delayed"]
DISRUPTED_FLIGHT_STATUSES = ["delayed", "cancelled"]


def aircraft_list(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    aircraft_qs = Aircraft.objects.select_related("airline").all()

    if query:
        aircraft_qs = aircraft_qs.filter(
            Q(registration_number__icontains=query)
            | Q(model__icontains=query)
            | Q(aircraft_type__icontains=query)
            | Q(airline__name__icontains=query)
        )

    if status in ["active", "maintenance", "inactive"]:
        aircraft_qs = aircraft_qs.filter(status=status)

    aircraft_qs = aircraft_qs.order_by("registration_number")

    paginator = Paginator(aircraft_qs, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    total_aircraft = Aircraft.objects.count()
    active_aircraft = Aircraft.objects.filter(status="active").count()
    maintenance_aircraft = Aircraft.objects.filter(status="maintenance").count()

    total_capacity = Aircraft.objects.aggregate(
        total=Sum("capacity")
    )["total"] or 0

    operators_count = (
        Aircraft.objects.exclude(airline__isnull=True)
        .values("airline")
        .distinct()
        .count()
    )

    context = {
        "aircraft_list": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "query": query,
        "status": status,
        "total_aircraft": total_aircraft,
        "active_aircraft": active_aircraft,
        "maintenance_aircraft": maintenance_aircraft,
        "total_capacity": total_capacity,
        "operators_count": operators_count,
    }

    return render(request, "aircraft/list.html", context)


def get_aircraft_data_quality_context(aircraft):
    fields = [
        ("Registration", bool(aircraft.registration_number)),
        ("Model", bool(aircraft.model)),
        ("Type", bool(aircraft.aircraft_type)),
        ("Operator", aircraft.airline is not None),
        ("Capacity", aircraft.capacity is not None and aircraft.capacity > 0),
        ("Status", bool(aircraft.status)),
    ]

    completed = sum(1 for field_name, is_complete in fields if is_complete)
    total = len(fields)
    score = round((completed / total) * 100) if total else 0

    missing_fields = [
        field_name for field_name, is_complete in fields if not is_complete
    ]

    if score >= 100:
        level = "complete"
        label = "Complete"
    elif score >= 60:
        level = "partial"
        label = "Partial"
    else:
        level = "minimal"
        label = "Minimal"

    return {
        "data_quality_score": score,
        "data_quality_level": level,
        "data_quality_label": label,
        "missing_data_fields": missing_fields,
    }


def aircraft_detail(request, pk):
    aircraft = get_object_or_404(
        Aircraft.objects.select_related("airline"),
        pk=pk,
    )

    linked_flights_qs = (
        Flight.objects.select_related(
            "airline",
            "origin_airport",
            "destination_airport",
            "aircraft",
        )
        .filter(aircraft=aircraft)
        .order_by("-scheduled_departure")
    )

    total_flights = linked_flights_qs.count()
    active_flights = linked_flights_qs.filter(status__in=ACTIVE_FLIGHT_STATUSES).count()
    disrupted_flights = linked_flights_qs.filter(status__in=DISRUPTED_FLIGHT_STATUSES).count()
    completed_flights = linked_flights_qs.filter(status__in=["landed", "cancelled"]).count()

    recent_flights = linked_flights_qs[:8]

    data_quality_context = get_aircraft_data_quality_context(aircraft)

    context = {
        "aircraft": aircraft,
        "total_flights": total_flights,
        "active_flights": active_flights,
        "disrupted_flights": disrupted_flights,
        "completed_flights": completed_flights,
        "recent_flights": recent_flights,
        **data_quality_context,
    }

    return render(request, "aircraft/detail.html", context)