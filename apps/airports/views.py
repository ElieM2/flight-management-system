from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from .models import Airport
from apps.flights.models import Flight


ACTIVE_FLIGHT_STATUSES = ["scheduled", "boarding", "departed", "in_air", "delayed"]
DISRUPTED_FLIGHT_STATUSES = ["delayed", "cancelled"]

NON_MEANINGFUL_TEXT_VALUES = {"", "unknown", "n/a", "null", "none", "—", "-"}


def is_meaningful_text(value):
    if value is None:
        return False

    cleaned = str(value).strip()

    if not cleaned:
        return False

    return cleaned.lower() not in NON_MEANINGFUL_TEXT_VALUES


def has_valid_coordinates(latitude, longitude):
    if latitude is None or longitude is None:
        return False

    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        return False

    if lat == 0 and lon == 0:
        return False

    return -90 <= lat <= 90 and -180 <= lon <= 180


def prepare_airport_display_data(airport):
    airport.has_coordinates = has_valid_coordinates(
        airport.latitude,
        airport.longitude,
    )

    airport.has_city = is_meaningful_text(airport.city)
    airport.has_country = is_meaningful_text(airport.country)

    airport.display_city = airport.city.strip() if airport.has_city else "Location not specified"
    airport.display_country = airport.country.strip() if airport.has_country else "Country not specified"
    airport.location_is_missing = not airport.has_city and not airport.has_country

    return airport


def get_airport_flight_relation_names():
    relation_names = []

    for relation in Airport._meta.related_objects:
        if relation.related_model == Flight:
            accessor_name = relation.get_accessor_name()
            if accessor_name:
                relation_names.append(accessor_name)

    return relation_names


def get_airport_flight_fk_field_names():
    field_names = []

    for field in Flight._meta.get_fields():
        if getattr(field, "is_relation", False) and getattr(field, "related_model", None) == Airport:
            if hasattr(field, "name"):
                field_names.append(field.name)

    return field_names


def get_linked_flights_count():
    airport_fk_fields = get_airport_flight_fk_field_names()

    if not airport_fk_fields:
        return 0

    linked_query = Q()

    for field_name in airport_fk_fields:
        linked_query |= Q(**{f"{field_name}__isnull": False})

    return Flight.objects.filter(linked_query).distinct().count()


def build_airport_flights_query(airport):
    airport_fk_fields = get_airport_flight_fk_field_names()

    if not airport_fk_fields:
        return Q(pk__isnull=True)

    airport_query = Q()

    for field_name in airport_fk_fields:
        airport_query |= Q(**{field_name: airport})

    return airport_query


def get_flight_route_display(flight):
    airport_fields = get_airport_flight_fk_field_names()

    origin = None
    destination = None

    preferred_origin_names = [
        "origin_airport",
        "departure_airport",
        "from_airport",
        "source_airport",
    ]

    preferred_destination_names = [
        "destination_airport",
        "arrival_airport",
        "to_airport",
        "target_airport",
    ]

    for field_name in preferred_origin_names:
        if field_name in airport_fields:
            origin = getattr(flight, field_name, None)
            break

    for field_name in preferred_destination_names:
        if field_name in airport_fields:
            destination = getattr(flight, field_name, None)
            break

    if origin and destination:
        origin_code = origin.iata_code or "—"
        destination_code = destination.iata_code or "—"
        return f"{origin_code} → {destination_code}"

    related_airports = []

    for field_name in airport_fields:
        airport = getattr(flight, field_name, None)
        if airport and airport.iata_code:
            related_airports.append(airport.iata_code)

    if len(related_airports) >= 2:
        return f"{related_airports[0]} → {related_airports[1]}"

    if len(related_airports) == 1:
        return related_airports[0]

    return "—"


def get_data_quality_context(airport):
    fields = [
        ("City", airport.has_city),
        ("Country", airport.has_country),
        ("Latitude", airport.has_coordinates),
        ("Longitude", airport.has_coordinates),
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
    elif score >= 50:
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


def airport_list(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    airports_qs = Airport.objects.all()

    if query:
        airports_qs = airports_qs.filter(
            Q(name__icontains=query)
            | Q(iata_code__icontains=query)
            | Q(icao_code__icontains=query)
            | Q(city__icontains=query)
            | Q(country__icontains=query)
        )

    if status == "active":
        airports_qs = airports_qs.filter(is_active=True)
    elif status == "inactive":
        airports_qs = airports_qs.filter(is_active=False)

    flight_relation_names = get_airport_flight_relation_names()

    annotations = {}

    for relation_name in flight_relation_names:
        annotations[f"{relation_name}_count"] = Count(relation_name, distinct=True)

    if annotations:
        airports_qs = airports_qs.annotate(**annotations)

    paginator = Paginator(airports_qs, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    for airport in page_obj.object_list:
        linked_flights_count = 0

        for relation_name in flight_relation_names:
            linked_flights_count += getattr(airport, f"{relation_name}_count", 0) or 0

        airport.linked_flights_count = linked_flights_count
        prepare_airport_display_data(airport)

    total_airports = Airport.objects.count()
    active_airports = Airport.objects.filter(is_active=True).count()

    countries_count = (
        Airport.objects.exclude(country__isnull=True)
        .exclude(country__exact="")
        .exclude(country__iexact="unknown")
        .exclude(country__iexact="n/a")
        .exclude(country__iexact="null")
        .exclude(country__iexact="none")
        .values("country")
        .distinct()
        .count()
    )

    linked_flights = get_linked_flights_count()

    context = {
        "airports": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "query": query,
        "status": status,
        "total_airports": total_airports,
        "active_airports": active_airports,
        "countries_count": countries_count,
        "linked_flights": linked_flights,
    }

    return render(request, "airports/list.html", context)


def airport_detail(request, pk):
    airport = get_object_or_404(Airport, pk=pk)
    prepare_airport_display_data(airport)

    airport_flights_query = build_airport_flights_query(airport)

    linked_flights_qs = Flight.objects.filter(airport_flights_query).distinct()

    total_flights = linked_flights_qs.count()
    active_flights = linked_flights_qs.filter(status__in=ACTIVE_FLIGHT_STATUSES).count()
    disrupted_flights = linked_flights_qs.filter(status__in=DISRUPTED_FLIGHT_STATUSES).count()

    airport_fk_fields = get_airport_flight_fk_field_names()

    departure_field_name = None
    arrival_field_name = None

    for candidate in ["origin_airport", "departure_airport", "from_airport", "source_airport"]:
        if candidate in airport_fk_fields:
            departure_field_name = candidate
            break

    for candidate in ["destination_airport", "arrival_airport", "to_airport", "target_airport"]:
        if candidate in airport_fk_fields:
            arrival_field_name = candidate
            break

    departure_count = (
        linked_flights_qs.filter(**{departure_field_name: airport}).count()
        if departure_field_name
        else 0
    )

    arrival_count = (
        linked_flights_qs.filter(**{arrival_field_name: airport}).count()
        if arrival_field_name
        else 0
    )

    if hasattr(Flight, "scheduled_departure"):
        recent_flights = linked_flights_qs.order_by("-scheduled_departure")[:8]
    else:
        recent_flights = linked_flights_qs.order_by("-id")[:8]

    for flight in recent_flights:
        flight.display_route = get_flight_route_display(flight)

    data_quality_context = get_data_quality_context(airport)

    context = {
        "airport": airport,
        "has_coordinates": airport.has_coordinates,
        "total_flights": total_flights,
        "departure_count": departure_count,
        "arrival_count": arrival_count,
        "active_flights": active_flights,
        "disrupted_flights": disrupted_flights,
        "recent_flights": recent_flights,
        **data_quality_context,
    }

    return render(request, "airports/detail.html", context)