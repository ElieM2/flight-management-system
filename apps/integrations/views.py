from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import ApiSyncLog
from .services.sync_service import FlightSyncService


RECENT_LOG_LIMIT = 20
DISPLAY_LOG_LIMIT = 5


def _build_user_safe_error_message(error_text):
    text = str(error_text).lower()

    if (
        'authentication' in text
        or 'invalid_access_key' in text
        or 'missing_access_key' in text
    ):
        return 'Sync failed: provider authentication error. Check the API key configuration.'

    if (
        'access was denied' in text
        or 'access restriction' in text
        or 'function_access_restricted' in text
    ):
        return 'Sync failed: provider access denied. Check API plan permissions or endpoint restrictions.'

    if (
        'rate or usage limit' in text
        or 'quota error' in text
        or 'usage_limit_reached' in text
        or 'rate_limit_reached' in text
    ):
        return 'Sync failed: provider usage or rate limit reached.'

    if 'network request failed' in text:
        return 'Sync failed: network communication with the provider failed.'

    if 'invalid json' in text:
        return 'Sync failed: provider returned an invalid response format.'

    return 'Sync failed: provider request could not be completed. Review the latest sync log.'


def _get_log_duration_seconds(log):
    if log and log.started_at and log.finished_at:
        return round((log.finished_at - log.started_at).total_seconds(), 1)

    return None


def _clean_sync_limit(value):
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return 10

    if limit < 1:
        return 1

    if limit > 100:
        return 100

    return limit


def _safe_rate(value, total):
    if not total:
        return 0

    return round((value / total) * 100, 1)


def _sum_logs(logs, field_name):
    total = 0

    for log in logs:
        total += getattr(log, field_name, 0) or 0

    return total


def _build_provider_health(latest_log, failure_rate):
    if not latest_log:
        return {
            'provider_health': 'No runs yet',
            'provider_health_class': 'neutral',
            'provider_health_reason': 'No synchronization has been executed yet.',
        }

    if latest_log.status == 'failed':
        return {
            'provider_health': 'Needs review',
            'provider_health_class': 'critical',
            'provider_health_reason': 'The latest synchronization failed. Check credentials, provider access or network response.',
        }

    if latest_log.records_received == 0:
        return {
            'provider_health': 'No data received',
            'provider_health_class': 'warning',
            'provider_health_reason': 'The latest run finished, but no external records were returned.',
        }

    if failure_rate >= 40:
        return {
            'provider_health': 'Recent review needed',
            'provider_health_class': 'warning',
            'provider_health_reason': 'Recent synchronization window contains too many runs requiring review.',
        }

    return {
        'provider_health': 'Available',
        'provider_health_class': 'stable',
        'provider_health_reason': 'Recent synchronization window is operational and external records were received.',
    }


def _build_timeline_highlights(
    latest_log,
    recent_total_runs,
    recent_success_rate,
    recent_total_received,
    recent_total_created,
    recent_total_updated,
):
    highlights = []

    if latest_log:
        highlights.append(
            f'Last run: {latest_log.provider_name} / {latest_log.sync_type} finished with status {latest_log.status.title()}.'
        )

    if recent_total_runs:
        highlights.append(
            f'{recent_total_runs} recent synchronization run(s) reviewed with {recent_success_rate}% success rate.'
        )

    if recent_total_received:
        highlights.append(
            f'{recent_total_received} external record(s) received in the recent synchronization window.'
        )

    if recent_total_created or recent_total_updated:
        highlights.append(
            f'{recent_total_created} record(s) created and {recent_total_updated} record(s) updated from recent external data.'
        )

    if not highlights:
        highlights.append(
            'No synchronization history is available yet. Run a controlled import to create the first trace.'
        )

    return highlights[:4]


@login_required
def sync_page(request):
    if request.method == 'POST':
        dep_iata = request.POST.get('dep_iata', '').strip().upper()
        arr_iata = request.POST.get('arr_iata', '').strip().upper()
        flight_iata = request.POST.get('flight_iata', '').strip().upper()
        limit = _clean_sync_limit(request.POST.get('limit') or 10)

        try:
            service = FlightSyncService()
            result = service.sync_flights(
                flight_iata=flight_iata or None,
                dep_iata=dep_iata or None,
                arr_iata=arr_iata or None,
                limit=limit,
            )

            messages.success(
                request,
                (
                    f'Sync completed — received: {result["received"]}, '
                    f'created: {result["created"]}, '
                    f'updated: {result["updated"]}, '
                    f'history entries: {result["history_created"]}, '
                    f'skipped local: {result["skipped_local"]}, '
                    f'skipped incomplete: {result["skipped_incomplete"]}.'
                )
            )
        except Exception as error:
            messages.error(request, _build_user_safe_error_message(error))

        return redirect('integrations:sync_page')

    recent_logs = list(ApiSyncLog.objects.all()[:RECENT_LOG_LIMIT])
    logs = recent_logs[:DISPLAY_LOG_LIMIT]
    latest_log = recent_logs[0] if recent_logs else None

    for log in recent_logs:
        log.duration_seconds = _get_log_duration_seconds(log)

    recent_success_count = sum(1 for log in recent_logs if log.status == 'success')
    recent_failed_count = sum(1 for log in recent_logs if log.status == 'failed')
    recent_total_runs = len(recent_logs)

    total_received = _sum_logs(recent_logs, 'records_received')
    total_created = _sum_logs(recent_logs, 'records_created')
    total_updated = _sum_logs(recent_logs, 'records_updated')

    success_rate = _safe_rate(recent_success_count, recent_total_runs)
    failure_rate = _safe_rate(recent_failed_count, recent_total_runs)

    durations = [
        log.duration_seconds
        for log in recent_logs
        if log.duration_seconds is not None
    ]

    average_duration_seconds = (
        round(sum(durations) / len(durations), 1)
        if durations
        else None
    )

    latest_status = latest_log.status.title() if latest_log else 'Unknown'
    latest_provider = (
        latest_log.provider_name
        if latest_log
        else FlightSyncService.PROVIDER_NAME
    )
    latest_received = latest_log.records_received if latest_log else 0
    latest_created = latest_log.records_created if latest_log else 0
    latest_updated = latest_log.records_updated if latest_log else 0
    latest_duration_seconds = _get_log_duration_seconds(latest_log)

    provider_health_context = _build_provider_health(
        latest_log=latest_log,
        failure_rate=failure_rate,
    )

    timeline_highlights = _build_timeline_highlights(
        latest_log=latest_log,
        recent_total_runs=recent_total_runs,
        recent_success_rate=success_rate,
        recent_total_received=total_received,
        recent_total_created=total_created,
        recent_total_updated=total_updated,
    )

    recent_failures = [
        log
        for log in recent_logs
        if log.status == 'failed'
    ][:DISPLAY_LOG_LIMIT]

    recent_successes = [
        log
        for log in recent_logs
        if log.status == 'success'
    ][:DISPLAY_LOG_LIMIT]

    context = {
        'logs': logs,
        'latest_log': latest_log,

        'latest_status': latest_status,
        'latest_provider': latest_provider,
        'latest_received': latest_received,
        'latest_created': latest_created,
        'latest_updated': latest_updated,
        'latest_duration_seconds': latest_duration_seconds,

        'success_count': recent_success_count,
        'failed_count': recent_failed_count,
        'total_runs': recent_total_runs,

        'total_received': total_received,
        'total_created': total_created,
        'total_updated': total_updated,

        'success_rate': success_rate,
        'failure_rate': failure_rate,
        'average_duration_seconds': average_duration_seconds,

        'timeline_highlights': timeline_highlights,
        'recent_failures': recent_failures,
        'recent_successes': recent_successes,

        **provider_health_context,
    }

    return render(request, 'integrations/sync.html', context)