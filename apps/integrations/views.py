from django.contrib import messages
from django.shortcuts import render, redirect
from .models import ApiSyncLog
from .services.sync_service import FlightSyncService


def sync_page(request):
    if request.method == 'POST':
        dep_iata = request.POST.get('dep_iata')
        arr_iata = request.POST.get('arr_iata')
        flight_iata = request.POST.get('flight_iata')
        limit = request.POST.get('limit') or 10

        try:
            service = FlightSyncService()
            result = service.sync_flights(
                flight_iata=flight_iata or None,
                dep_iata=dep_iata or None,
                arr_iata=arr_iata or None,
                limit=int(limit)
            )
            messages.success(
                request,
                f"Sync success - received: {result['received']}, "
                f"created: {result['created']}, updated: {result['updated']}"
            )
        except Exception as e:
            messages.error(request, f"Sync failed: {e}")

        return redirect('sync_page')

    logs = ApiSyncLog.objects.all()[:10]
    return render(request, 'integrations/sync.html', {'logs': logs})