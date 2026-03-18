from django.shortcuts import render
from apps.airlines.models import Airline
from apps.airports.models import Airport
from apps.aircraft.models import Aircraft
from apps.flights.models import Flight


def dashboard_home(request):
    total_flights = Flight.objects.count()
    total_airlines = Airline.objects.count()
    total_airports = Airport.objects.count()
    total_aircraft = Aircraft.objects.count()

    scheduled_count = Flight.objects.filter(status='scheduled').count()
    boarding_count = Flight.objects.filter(status='boarding').count()
    departed_count = Flight.objects.filter(status='departed').count()
    in_air_count = Flight.objects.filter(status='in_air').count()
    landed_count = Flight.objects.filter(status='landed').count()
    delayed_count = Flight.objects.filter(status='delayed').count()
    cancelled_count = Flight.objects.filter(status='cancelled').count()

    airlines = Airline.objects.all()
    airline_names = []
    airline_flight_counts = []

    for airline in airlines:
        airline_names.append(airline.name)
        airline_flight_counts.append(airline.flights.count())

    recent_flights = Flight.objects.select_related(
        'airline',
        'origin_airport',
        'destination_airport'
    )[:5]

    status_chart_data = {
        'labels': [
            'Scheduled',
            'Boarding',
            'Departed',
            'In Air',
            'Landed',
            'Delayed',
            'Cancelled',
        ],
        'values': [
            scheduled_count,
            boarding_count,
            departed_count,
            in_air_count,
            landed_count,
            delayed_count,
            cancelled_count,
        ]
    }

    airline_chart_data = {
        'labels': airline_names,
        'values': airline_flight_counts,
    }

    context = {
        'total_flights': total_flights,
        'total_airlines': total_airlines,
        'total_airports': total_airports,
        'total_aircraft': total_aircraft,
        'recent_flights': recent_flights,
        'status_chart_data': status_chart_data,
        'airline_chart_data': airline_chart_data,
    }

    return render(request, 'dashboard/index.html', context)