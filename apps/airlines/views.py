from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from .models import Airline
from apps.flights.models import Flight


AIRLINE_ACTIVE_STATUSES = [
    "scheduled",
    "boarding",
    "departed",
    "in_air",
    "delayed",
]

AIRLINE_DISRUPTED_STATUSES = [
    "delayed",
    "cancelled",
]

NON_MEANINGFUL_TEXT_VALUES = {
    "",
    "unknown",
    "n/a",
    "null",
    "none",
    "—",
    "-",
}


def is_meaningful_text(value):
    if value is None:
        return False

    cleaned = str(value).strip()

    if not cleaned:
        return False

    return cleaned.lower() not in NON_MEANINGFUL_TEXT_VALUES


def airline_list(request):
    query = request.GET.get("q", "").strip()
    page_number = request.GET.get("page", 1)

    airlines_qs = (
        Airline.objects
        .all()
        .annotate(
            flight_count=Count("flights", distinct=True)
        )
        .order_by("name")
    )

    if query:
        airlines_qs = airlines_qs.filter(
            Q(name__icontains=query)
            | Q(iata_code__icontains=query)
            | Q(icao_code__icontains=query)
            | Q(country__icontains=query)
            | Q(country_code__icontains=query)
        )

    paginator = Paginator(airlines_qs, 12)
    page_obj = paginator.get_page(page_number)

    total_airlines = Airline.objects.count()
    total_active_airlines = Airline.objects.filter(is_active=True).count()
    total_flights = Flight.objects.count()

    total_countries = (
        Airline.objects
        .exclude(country__isnull=True)
        .exclude(country__exact="")
        .exclude(country__iexact="unknown")
        .exclude(country__iexact="n/a")
        .exclude(country__iexact="null")
        .exclude(country__iexact="none")
        .values("country_code")
        .distinct()
        .count()
    )

    context = {
        "airlines": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "query": query,
        "total_airlines": total_airlines,
        "total_active_airlines": total_active_airlines,
        "total_countries": total_countries,
        "total_flights": total_flights,
    }

    return render(request, "airlines/list.html", context)


def airline_detail(request, pk):
    airline = get_object_or_404(Airline, pk=pk)

    recent_flights_qs = (
        Flight.objects
        .filter(airline=airline)
        .select_related(
            "origin_airport",
            "destination_airport",
            "aircraft",
        )
        .order_by("-scheduled_departure")
    )

    total_flights = recent_flights_qs.count()

    active_flights = recent_flights_qs.filter(
        status__in=AIRLINE_ACTIVE_STATUSES
    ).count()

    disrupted_flights = recent_flights_qs.filter(
        status__in=AIRLINE_DISRUPTED_STATUSES
    ).count()

    completed_flights = recent_flights_qs.filter(
        status="landed"
    ).count()

    aircraft_count = (
        recent_flights_qs
        .exclude(aircraft__isnull=True)
        .values("aircraft")
        .distinct()
        .count()
    )

    if total_flights == 0:
        operational_note = (
            "No recent flight activity is currently visible for this airline."
        )
    elif disrupted_flights > 0 and active_flights > 0:
        operational_note = (
            "This airline has active operations with visible disruption pressure."
        )
    elif active_flights > 0:
        operational_note = (
            "This airline currently has active flight activity in the platform."
        )
    elif completed_flights > 0:
        operational_note = (
            "Recent completed operations are available for this airline."
        )
    else:
        operational_note = (
            "Operational visibility is currently limited for this airline."
        )

    context = {
        "airline": airline,
        "total_flights": total_flights,
        "active_flights": active_flights,
        "disrupted_flights": disrupted_flights,
        "completed_flights": completed_flights,
        "aircraft_count": aircraft_count,
        "recent_flights": recent_flights_qs[:10],
        "operational_note": operational_note,
    }

    return render(request, "airlines/detail.html", context)