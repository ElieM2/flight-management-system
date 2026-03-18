from django.shortcuts import render, get_object_or_404
from .models import Flight


def flight_list(request):
    flights = Flight.objects.select_related(
        'airline',
        'aircraft',
        'origin_airport',
        'destination_airport'
    ).all()

    context = {
        'flights': flights
    }
    return render(request, 'flights/list.html', context)


def flight_detail(request, pk):
    flight = get_object_or_404(
        Flight.objects.select_related(
            'airline',
            'aircraft',
            'origin_airport',
            'destination_airport'
        ),
        pk=pk
    )

    context = {
        'flight': flight
    }
    return render(request, 'flights/detail.html', context)