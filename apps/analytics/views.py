from django.db.models import Count, Q
from django.shortcuts import render
from django.utils.translation import gettext as _

from apps.flights.models import Flight


STATUS_ORDER = [
    'scheduled',
    'boarding',
    'departed',
    'in_air',
    'landed',
    'delayed',
    'cancelled',
]

SOURCE_ORDER = [
    'api',
    'local',
]


def _status_label(status_key):
    labels = {
        'scheduled': _('Scheduled'),
        'boarding': _('Boarding'),
        'departed': _('Departed'),
        'in_air': _('In Air'),
        'landed': _('Landed'),
        'delayed': _('Delayed'),
        'cancelled': _('Cancelled'),
    }

    return labels.get(status_key, _('Unknown'))


def _source_label(source_key):
    labels = {
        'api': _('API synchronized'),
        'local': _('Local records'),
    }

    return labels.get(source_key, _('Unspecified source'))


def _safe_rate(value, total):
    if not total:
        return 0

    return round((value / total) * 100, 1)


def _get_selected_airline_id(request):
    selected_airline = request.GET.get('airline', 'all')

    if selected_airline in ['', 'all', None]:
        return None

    try:
        return int(selected_airline)
    except (TypeError, ValueError):
        return None


def _base_flights_queryset():
    return Flight.objects.select_related(
        'airline',
        'origin_airport',
        'destination_airport',
        'aircraft',
    )


def _flight_field_exists(field_name):
    try:
        Flight._meta.get_field(field_name)
        return True
    except Exception:
        return False


def _combine_q(expressions, connector='or'):
    if not expressions:
        return Q(pk__in=[])

    combined = expressions[0]

    for expression in expressions[1:]:
        if connector == 'and':
            combined = combined & expression
        else:
            combined = combined | expression

    return combined


def _build_high_risk_query():
    expressions = []

    if _flight_field_exists('risk_level'):
        expressions.append(Q(risk_level__in=['high', 'critical']))

    if _flight_field_exists('operational_risk_level'):
        expressions.append(Q(operational_risk_level__in=['high', 'critical']))

    if _flight_field_exists('priority'):
        expressions.append(Q(priority__in=['high', 'critical', 'immediate']))

    if _flight_field_exists('operational_priority'):
        expressions.append(Q(operational_priority__in=['high', 'critical', 'immediate']))

    if _flight_field_exists('risk_score'):
        expressions.append(Q(risk_score__gte=82))

    if _flight_field_exists('operational_risk_score'):
        expressions.append(Q(operational_risk_score__gte=82))

    if _flight_field_exists('disruption_score'):
        expressions.append(Q(disruption_score__gte=25))

    if _flight_field_exists('impact_score'):
        expressions.append(Q(impact_score__gte=25))

    if _flight_field_exists('route_alert'):
        expressions.append(Q(route_alert__in=['critical', 'storm']))

    if _flight_field_exists('route_exposure'):
        expressions.append(Q(route_exposure__in=['critical', 'storm']))

    if _flight_field_exists('alert_level'):
        expressions.append(Q(alert_level__in=['high', 'critical']))

    return _combine_q(expressions)


def _build_attention_query():
    expressions = []

    if _flight_field_exists('risk_level'):
        expressions.append(Q(risk_level__in=['medium', 'attention']))

    if _flight_field_exists('operational_risk_level'):
        expressions.append(Q(operational_risk_level__in=['medium', 'attention']))

    if _flight_field_exists('priority'):
        expressions.append(Q(priority__in=['attention', 'warning']))

    if _flight_field_exists('operational_priority'):
        expressions.append(Q(operational_priority__in=['attention', 'warning']))

    if _flight_field_exists('risk_score'):
        expressions.append(Q(risk_score__gte=45, risk_score__lt=82))

    if _flight_field_exists('operational_risk_score'):
        expressions.append(Q(operational_risk_score__gte=45, operational_risk_score__lt=82))

    if _flight_field_exists('disruption_score'):
        expressions.append(Q(disruption_score__gte=10, disruption_score__lt=25))

    if _flight_field_exists('impact_score'):
        expressions.append(Q(impact_score__gte=10, impact_score__lt=25))

    if _flight_field_exists('route_alert'):
        expressions.append(Q(route_alert__in=['attention', 'weather', 'wind', 'operational']))

    if _flight_field_exists('route_exposure'):
        expressions.append(Q(route_exposure__in=['attention', 'weather', 'wind', 'operational']))

    if _flight_field_exists('alert_level'):
        expressions.append(Q(alert_level__in=['medium', 'attention', 'warning']))

    return _combine_q(expressions)


def _build_intelligence_context(request, active_page='overview'):
    base_flights = _base_flights_queryset()

    selected_status = request.GET.get('status', 'all')
    selected_source = request.GET.get('source', 'all')
    selected_airline_id = _get_selected_airline_id(request)

    flights = base_flights

    if selected_status in STATUS_ORDER:
        flights = flights.filter(status=selected_status)
    else:
        selected_status = 'all'

    if selected_source in SOURCE_ORDER:
        flights = flights.filter(source_type=selected_source)
    else:
        selected_source = 'all'

    if selected_airline_id:
        flights = flights.filter(airline_id=selected_airline_id)

    is_filtered = (
        selected_status != 'all'
        or selected_source != 'all'
        or selected_airline_id is not None
    )

    base_total_flights = base_flights.count()
    total_flights = flights.count()

    delayed_count = flights.filter(status='delayed').count()
    cancelled_count = flights.filter(status='cancelled').count()
    active_count = flights.filter(status__in=['boarding', 'departed', 'in_air']).count()
    landed_count = flights.filter(status='landed').count()
    scheduled_count = flights.filter(status='scheduled').count()

    api_count = flights.filter(source_type='api').count()
    local_count = flights.filter(source_type='local').count()
    unknown_source_count = max(total_flights - api_count - local_count, 0)

    high_risk_query = _build_high_risk_query()
    attention_risk_query = _build_attention_query()

    critical_query = Q(status='cancelled') | high_risk_query
    attention_query = (Q(status='delayed') | attention_risk_query) & ~critical_query

    critical_count = flights.filter(critical_query).distinct().count()
    attention_count = flights.filter(attention_query).distinct().count()
    high_risk_count = flights.filter(high_risk_query).exclude(status='cancelled').distinct().count()
    medium_risk_count = flights.filter(attention_risk_query).exclude(critical_query).exclude(status='delayed').distinct().count()

    irregular_ops_count = critical_count + attention_count
    disruption_count = irregular_ops_count
    stable_count = max(total_flights - irregular_ops_count, 0)

    delay_rate = _safe_rate(delayed_count, total_flights)
    cancellation_rate = _safe_rate(cancelled_count, total_flights)
    active_rate = _safe_rate(active_count, total_flights)
    critical_rate = _safe_rate(critical_count, total_flights)
    attention_rate = _safe_rate(attention_count, total_flights)
    irregular_ops_rate = _safe_rate(irregular_ops_count, total_flights)
    disruption_rate = irregular_ops_rate
    data_coverage_rate = _safe_rate(api_count, total_flights)
    local_rate = _safe_rate(local_count, total_flights)
    completion_rate = _safe_rate(landed_count, total_flights)

    clean_operations = max(total_flights - irregular_ops_count, 0)
    base_score = (clean_operations / total_flights) * 100 if total_flights else 0
    confidence_penalty = max(0, 5 - total_flights) * 2 if total_flights else 0
    performance_score = max(round(base_score - confidence_penalty, 1), 0)

    if performance_score >= 90:
        score_label = _('Strong operating quality')
    elif performance_score >= 75:
        score_label = _('Good performance with visible pressure')
    elif performance_score >= 55:
        score_label = _('Moderate performance requiring attention')
    else:
        score_label = _('High operational pressure')

    status_counts_raw = flights.values('status').annotate(total=Count('id')).order_by()
    status_map = {item['status']: item['total'] for item in status_counts_raw}

    status_rows = [
        {
            'key': key,
            'label': _status_label(key),
            'total': status_map.get(key, 0),
            'rate': _safe_rate(status_map.get(key, 0), total_flights),
        }
        for key in STATUS_ORDER
    ]

    status_labels = [item['label'] for item in status_rows]
    status_values = [item['total'] for item in status_rows]

    dominant_status_key = max(status_map, key=status_map.get) if status_map else None
    dominant_status = _status_label(dominant_status_key) if dominant_status_key else _('No data')

    top_airlines_raw = (
        flights.values('airline__name')
        .annotate(total=Count('id'))
        .order_by('-total', 'airline__name')[:5]
    )

    top_airlines = [
        {
            'name': item['airline__name'] or _('Unknown airline'),
            'total': item['total'],
            'share': _safe_rate(item['total'], total_flights),
        }
        for item in top_airlines_raw
    ]

    top_airlines_labels = [item['name'] for item in top_airlines]
    top_airlines_values = [item['total'] for item in top_airlines]

    top_routes_raw = (
        flights.values('origin_airport__iata_code', 'destination_airport__iata_code')
        .annotate(total=Count('id'))
        .order_by('-total', 'origin_airport__iata_code')[:8]
    )

    top_routes = [
        {
            'route': (
                f"{item['origin_airport__iata_code'] or '--'}"
                f" → "
                f"{item['destination_airport__iata_code'] or '--'}"
            ),
            'total': item['total'],
            'share': _safe_rate(item['total'], total_flights),
        }
        for item in top_routes_raw
    ]

    top_routes_labels = [item['route'] for item in top_routes[:5]]
    top_routes_values = [item['total'] for item in top_routes[:5]]

    top_origin_airports_raw = (
        flights.values(
            'origin_airport__iata_code',
            'origin_airport__name',
            'origin_airport__city',
        )
        .annotate(total=Count('id'))
        .order_by('-total', 'origin_airport__iata_code')[:5]
    )

    top_origin_airports = [
        {
            'code': item['origin_airport__iata_code'] or '--',
            'name': item['origin_airport__name'] or item['origin_airport__city'] or _('Unknown airport'),
            'total': item['total'],
            'share': _safe_rate(item['total'], total_flights),
        }
        for item in top_origin_airports_raw
    ]

    top_destination_airports_raw = (
        flights.values(
            'destination_airport__iata_code',
            'destination_airport__name',
            'destination_airport__city',
        )
        .annotate(total=Count('id'))
        .order_by('-total', 'destination_airport__iata_code')[:5]
    )

    top_destination_airports = [
        {
            'code': item['destination_airport__iata_code'] or '--',
            'name': item['destination_airport__name'] or item['destination_airport__city'] or _('Unknown airport'),
            'total': item['total'],
            'share': _safe_rate(item['total'], total_flights),
        }
        for item in top_destination_airports_raw
    ]

    airline_filter_options_raw = (
        base_flights.exclude(airline__isnull=True)
        .values('airline__id', 'airline__name')
        .annotate(total=Count('id'))
        .order_by('airline__name')
    )

    airline_filter_options = [
        {
            'id': item['airline__id'],
            'name': item['airline__name'] or _('Unknown airline'),
            'total': item['total'],
        }
        for item in airline_filter_options_raw
    ]

    most_active_airline = top_airlines[0]['name'] if top_airlines else _('No data')
    busiest_route = top_routes[0]['route'] if top_routes else _('No data')

    if critical_count >= 3 or critical_rate >= 8:
        monitoring_mode = _('Critical Supervision')
        supervision_class = 'critical'
        report_narrative = _(
            'Critical operational pressure is visible. Prioritize cancelled flights, high-risk records, '
            'and the busiest corridor before expanding the analysis.'
        )
    elif attention_count >= 2 or irregular_ops_rate >= 5:
        monitoring_mode = _('Elevated Supervision')
        supervision_class = 'elevated'
        report_narrative = _(
            'Operations remain readable, but delayed flights and attention-level records require targeted monitoring.'
        )
    else:
        monitoring_mode = _('Stable Operations')
        supervision_class = 'stable'
        report_narrative = _(
            'The visible operational picture is stable. Continue standard supervision and data validation.'
        )

    recommendations = []

    if not total_flights:
        recommendations.append(
            _('No flight records are visible in this report. Check filters or synchronize operational data.')
        )

    if critical_count > 0:
        recommendations.append(
            _('Review critical records first: cancelled flights and high-risk operations require priority handling.')
        )

    if attention_count > 0:
        recommendations.append(
            _('Keep attention flights under monitoring and compare them with route concentration and airport activity.')
        )

    if cancelled_count > 0:
        recommendations.append(
            _('Validate recovery actions for cancelled flights before presenting the operational report.')
        )

    if delayed_count > 0:
        recommendations.append(
            _('Track delayed flights and identify whether the pressure is concentrated on specific corridors.')
        )

    if irregular_ops_rate >= 10:
        recommendations.append(
            _('Irregular operations share is high. Treat the current report as an attention-required operating view.')
        )

    if api_count > local_count and api_count > 0:
        recommendations.append(
            _('External synchronized data is dominant. Explain this as a hybrid data model supported by API ingestion.')
        )

    if local_count > api_count and local_count > 0:
        recommendations.append(
            _('Local records are dominant. Explain this as manual control over the internal operational database.')
        )

    if top_routes:
        recommendations.append(
            _('Priority corridor to watch: %(route)s.') % {
                'route': top_routes[0]['route'],
            }
        )

    if not recommendations:
        recommendations.append(
            _('Operations are stable. Maintain standard supervision and data validation.')
        )

    source_labels = [
        _source_label('api'),
        _source_label('local'),
        _('Unspecified source'),
    ]

    source_values = [
        api_count,
        local_count,
        unknown_source_count,
    ]

    disruption_mix_labels = [
        _('Critical records'),
        _('Attention records'),
        _('Stable records'),
    ]

    disruption_mix_values = [
        critical_count,
        attention_count,
        stable_count,
    ]

    legacy_disruption_mix_labels = [
        _('Delayed'),
        _('Cancelled'),
        _('Other records'),
    ]

    legacy_disruption_mix_values = [
        delayed_count,
        cancelled_count,
        max(total_flights - delayed_count - cancelled_count, 0),
    ]

    recent_flights = flights.order_by('-id')[:10]

    return {
        'active_page': active_page,

        'base_total_flights': base_total_flights,
        'total_flights': total_flights,

        'scheduled_count': scheduled_count,
        'delayed_count': delayed_count,
        'cancelled_count': cancelled_count,
        'active_count': active_count,
        'landed_count': landed_count,

        'api_count': api_count,
        'local_count': local_count,
        'unknown_source_count': unknown_source_count,

        'critical_count': critical_count,
        'attention_count': attention_count,
        'high_risk_count': high_risk_count,
        'medium_risk_count': medium_risk_count,
        'irregular_ops_count': irregular_ops_count,

        'disruption_count': disruption_count,
        'stable_count': stable_count,

        'delay_rate': delay_rate,
        'cancellation_rate': cancellation_rate,
        'active_rate': active_rate,
        'critical_rate': critical_rate,
        'attention_rate': attention_rate,
        'irregular_ops_rate': irregular_ops_rate,
        'disruption_rate': disruption_rate,
        'data_coverage_rate': data_coverage_rate,
        'local_rate': local_rate,
        'completion_rate': completion_rate,

        'performance_score': performance_score,
        'score_label': score_label,

        'dominant_status': dominant_status,
        'most_active_airline': most_active_airline,
        'busiest_route': busiest_route,
        'monitoring_mode': monitoring_mode,
        'supervision_class': supervision_class,
        'report_narrative': report_narrative,

        'recommendations': recommendations,
        'recent_flights': recent_flights,

        'status_rows': status_rows,
        'status_labels': status_labels,
        'status_values': status_values,

        'top_airlines': top_airlines,
        'top_airlines_labels': top_airlines_labels,
        'top_airlines_values': top_airlines_values,

        'top_routes': top_routes,
        'top_routes_labels': top_routes_labels,
        'top_routes_values': top_routes_values,

        'top_origin_airports': top_origin_airports,
        'top_destination_airports': top_destination_airports,

        'source_labels': source_labels,
        'source_values': source_values,

        'disruption_mix_labels': disruption_mix_labels,
        'disruption_mix_values': disruption_mix_values,

        'legacy_disruption_mix_labels': legacy_disruption_mix_labels,
        'legacy_disruption_mix_values': legacy_disruption_mix_values,

        'airline_filter_options': airline_filter_options,
        'selected_status': selected_status,
        'selected_source': selected_source,
        'selected_airline_id': selected_airline_id,
        'is_filtered': is_filtered,
    }


def analytics_home(request):
    context = _build_intelligence_context(request, active_page='overview')
    return render(request, 'analytics/index.html', context)


def analytics_reports(request):
    context = _build_intelligence_context(request, active_page='reports')
    return render(request, 'analytics/reports.html', context)


def analytics_charts(request):
    context = _build_intelligence_context(request, active_page='charts')
    return render(request, 'analytics/charts.html', context)


def analytics_routes(request):
    context = _build_intelligence_context(request, active_page='routes')
    return render(request, 'analytics/routes.html', context)


def analytics_reliability(request):
    context = _build_intelligence_context(request, active_page='reliability')
    return render(request, 'analytics/reliability.html', context)


def analytics_feedback(request):
    context = _build_intelligence_context(request, active_page='feedback')
    return render(request, 'analytics/feedback.html', context)