from django.shortcuts import render
from apps.flights.models import Flight


def monitoring_home(request):
    flights = Flight.objects.select_related(
        'airline',
        'aircraft',
        'origin_airport',
        'destination_airport'
    ).all()

    context = {
        'flights': flights,
        'total_flights': flights.count(),
        'scheduled_count': flights.filter(status='scheduled').count(),
        'boarding_count': flights.filter(status='boarding').count(),
        'active_count': flights.exclude(status='landed').exclude(status='cancelled').count(),
    }
    return render(request, 'monitoring/index.html', context)


def map_view(request):
    flights = Flight.objects.select_related(
        'airline',
        'origin_airport',
        'destination_airport'
    ).all()

    flights_data = []
    for flight in flights:
        flights_data.append({
            'flight_number': flight.flight_number,
            'airline': flight.airline.name,
            'status': flight.status,
            'status_display': flight.get_status_display(),
            'origin_name': flight.origin_airport.name,
            'origin_iata': flight.origin_airport.iata_code,
            'origin_lat': float(flight.origin_airport.latitude),
            'origin_lng': float(flight.origin_airport.longitude),
            'destination_name': flight.destination_airport.name,
            'destination_iata': flight.destination_airport.iata_code,
            'destination_lat': float(flight.destination_airport.latitude),
            'destination_lng': float(flight.destination_airport.longitude),
        })

    return render(request, 'monitoring/map.html', {
        'flights_json': flights_data
    })