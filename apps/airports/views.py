from django.shortcuts import render
from .models import Airport


def airport_list(request):
    airports = Airport.objects.all()
    return render(request, 'airports/list.html', {'airports': airports})