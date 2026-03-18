from django.contrib import admin
from .models import ApiSyncLog


@admin.register(ApiSyncLog)
class ApiSyncLogAdmin(admin.ModelAdmin):
    list_display = (
        'provider_name',
        'sync_type',
        'status',
        'records_received',
        'records_created',
        'records_updated',
        'started_at',
        'finished_at',
    )
    list_filter = ('provider_name', 'status', 'sync_type')
    search_fields = ('provider_name', 'sync_type', 'message')