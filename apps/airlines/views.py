from django.shortcuts import render
from .models import Airline


def airline_list(request):
    airlines = Airline.objects.all()
    return render(request, 'airlines/list.html', {'airlines': airlines})