from django.shortcuts import render
from .models import Aircraft


def aircraft_list(request):
    aircraft_list = Aircraft.objects.select_related('airline').all()
    return render(request, 'aircraft/list.html', {'aircraft_list': aircraft_list})