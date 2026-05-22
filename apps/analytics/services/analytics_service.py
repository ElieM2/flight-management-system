from django.db.models import Count, Q, Avg
from django.db.models.functions import TruncDate

from apps.flights.models import Flight, FlightStatusHistory


class AnalyticsService:
    @staticmethod
    def calculate_delay_risk(airline_stats, route_stats, airline_name, route_key):
        airline = next((a for a in airline_stats if a['airline_name'] == airline_name), None)
        route = next((r for r in route_stats if r['route_key'] == route_key), None)

        risk = 5.0

        if airline and airline['total'] > 0:
            delay_rate = airline['delays'] / airline['total']
            cancel_rate = airline['cancellations'] / airline['total']

            risk += delay_rate * 45
            risk += cancel_rate * 75

            if airline['score'] < 60:
                risk += 25
            elif airline['score'] < 75:
                risk += 15
            elif airline['score'] < 85:
                risk += 8

            if airline['total'] < 5:
                risk += 10
            elif airline['total'] < 10:
                risk += 5

        if route:
            if route['critical_events'] >= 5:
                risk += 30
            elif route['critical_events'] >= 3:
                risk += 20
            elif route['critical_events'] >= 1:
                risk += 10

            if route['stability_score'] < 60:
                risk += 18
            elif route['stability_score'] < 75:
                risk += 10

        return round(min(risk, 100), 1)

    @staticmethod
    def get_top_disrupted_airlines():
        return list(
            FlightStatusHistory.objects
            .filter(new_status__in=['delayed', 'cancelled'])
            .values('flight__airline__name')
            .annotate(total=Count('id'))
            .order_by('-total', 'flight__airline__name')[:8]
        )

    @staticmethod
    def get_top_disrupted_routes():
        raw_routes = list(
            FlightStatusHistory.objects
            .filter(new_status__in=['delayed', 'cancelled'])
            .values('flight__origin_airport__iata_code', 'flight__destination_airport__iata_code')
            .annotate(total=Count('id'))
            .order_by('-total', 'flight__origin_airport__iata_code', 'flight__destination_airport__iata_code')[:8]
        )

        routes = []
        for item in raw_routes:
            origin = item['flight__origin_airport__iata_code'] or '---'
            destination = item['flight__destination_airport__iata_code'] or '---'
            routes.append({
                'origin_iata': origin,
                'destination_iata': destination,
                'route_key': f'{origin} → {destination}',
                'total': item['total'],
            })
        return routes

    @staticmethod
    def get_daily_disruptions():
        return (
            FlightStatusHistory.objects
            .filter(new_status__in=['delayed', 'cancelled'])
            .annotate(day=TruncDate('changed_at'))
            .values('day', 'new_status')
            .annotate(total=Count('id'))
            .order_by('day')
        )

    @staticmethod
    def get_current_status_distribution():
        return (
            Flight.objects
            .values('status')
            .annotate(total=Count('id'))
            .order_by('-total')
        )

    @staticmethod
    def get_airline_stats():
        raw_stats = list(
            FlightStatusHistory.objects
            .values('flight__airline__name')
            .annotate(
                total=Count('id'),
                delays=Count('id', filter=Q(new_status='delayed')),
                cancellations=Count('id', filter=Q(new_status='cancelled')),
                in_air=Count('id', filter=Q(new_status='in_air')),
                scheduled=Count('id', filter=Q(new_status='scheduled')),
                boarding=Count('id', filter=Q(new_status='boarding')),
                landed=Count('id', filter=Q(new_status='landed')),
                avg_departure_delay=Avg('departure_delay_minutes'),
                avg_arrival_delay=Avg('arrival_delay_minutes'),
            )
            .order_by('flight__airline__name')
        )

        filtered_airline_stats = []

        for stat in raw_stats:
            airline_name = stat['flight__airline__name']
            if not airline_name or stat['total'] < 3:
                continue

            clean_operations = stat['total'] - stat['delays'] - stat['cancellations']
            base_score = (clean_operations / stat['total']) * 100 if stat['total'] else 0

            confidence_factor = min(stat['total'] / 15, 1)
            confidence_adjustment = 0.7 + 0.3 * confidence_factor

            penalty = (stat['delays'] * 4) + (stat['cancellations'] * 12)

            avg_departure_delay = stat['avg_departure_delay'] or 0
            avg_arrival_delay = stat['avg_arrival_delay'] or 0
            delay_penalty = min(avg_departure_delay * 0.3, 10) + min(avg_arrival_delay * 0.3, 10)

            raw_score = (base_score * confidence_adjustment) - penalty - delay_penalty

            if raw_score < 0:
                raw_score = 0
            elif raw_score > 100:
                raw_score = 100

            disruption_ratio = (stat['delays'] + stat['cancellations']) / stat['total'] if stat['total'] else 0

            if disruption_ratio >= 0.30:
                anomaly = True
                anomaly_message = f"Anomaly detected: {airline_name} shows abnormal disruption frequency."
            else:
                anomaly = False
                anomaly_message = ''

            if raw_score >= 90:
                rating = 'Excellent'
            elif raw_score >= 80:
                rating = 'Good'
            elif raw_score >= 65:
                rating = 'Average'
            else:
                rating = 'Risk'

            filtered_airline_stats.append({
                'airline_name': airline_name,
                'total': stat['total'],
                'delays': stat['delays'],
                'cancellations': stat['cancellations'],
                'in_air': stat['in_air'],
                'scheduled': stat['scheduled'],
                'boarding': stat['boarding'],
                'landed': stat['landed'],
                'avg_departure_delay': round(avg_departure_delay, 1) if avg_departure_delay else 0,
                'avg_arrival_delay': round(avg_arrival_delay, 1) if avg_arrival_delay else 0,
                'score': round(raw_score, 1),
                'rating': rating,
                'anomaly': anomaly,
                'anomaly_message': anomaly_message,
            })

        return filtered_airline_stats

    @staticmethod
    def get_route_stats():
        raw_stats = list(
            FlightStatusHistory.objects
            .values('flight__origin_airport__iata_code', 'flight__destination_airport__iata_code')
            .annotate(
                total=Count('id'),
                delays=Count('id', filter=Q(new_status='delayed')),
                cancellations=Count('id', filter=Q(new_status='cancelled')),
                avg_departure_delay=Avg('departure_delay_minutes'),
                avg_arrival_delay=Avg('arrival_delay_minutes'),
            )
            .order_by('flight__origin_airport__iata_code', 'flight__destination_airport__iata_code')
        )

        route_stats = []

        for stat in raw_stats:
            origin = stat['flight__origin_airport__iata_code'] or '---'
            destination = stat['flight__destination_airport__iata_code'] or '---'
            route_key = f'{origin} → {destination}'

            if stat['total'] < 2:
                continue

            clean_operations = stat['total'] - stat['delays'] - stat['cancellations']
            base_score = (clean_operations / stat['total']) * 100 if stat['total'] else 0

            avg_departure_delay = stat['avg_departure_delay'] or 0
            avg_arrival_delay = stat['avg_arrival_delay'] or 0
            delay_penalty = min(avg_departure_delay * 0.35, 12) + min(avg_arrival_delay * 0.35, 12)
            disruption_penalty = (stat['delays'] * 3) + (stat['cancellations'] * 10)

            stability_score = base_score - delay_penalty - disruption_penalty
            stability_score = max(0, min(100, stability_score))

            if stability_score >= 90:
                rating = 'Excellent'
            elif stability_score >= 80:
                rating = 'Good'
            elif stability_score >= 65:
                rating = 'Average'
            else:
                rating = 'Risk'

            route_stats.append({
                'origin_iata': origin,
                'destination_iata': destination,
                'route_key': route_key,
                'total': stat['total'],
                'delays': stat['delays'],
                'cancellations': stat['cancellations'],
                'critical_events': stat['delays'] + stat['cancellations'],
                'avg_departure_delay': round(avg_departure_delay, 1) if avg_departure_delay else 0,
                'avg_arrival_delay': round(avg_arrival_delay, 1) if avg_arrival_delay else 0,
                'stability_score': round(stability_score, 1),
                'rating': rating,
            })

        return route_stats

    @staticmethod
    def build_trend_chart_data(daily_disruptions):
        trend_map = {}

        for item in daily_disruptions:
            day_str = item['day'].strftime('%Y-%m-%d') if item['day'] else 'Unknown'
            if day_str not in trend_map:
                trend_map[day_str] = {'delayed': 0, 'cancelled': 0}
            trend_map[day_str][item['new_status']] = item['total']

        trend_labels = list(trend_map.keys())
        delayed_values = [trend_map[day]['delayed'] for day in trend_labels]
        cancelled_values = [trend_map[day]['cancelled'] for day in trend_labels]

        return {
            'labels': trend_labels,
            'delayed': delayed_values,
            'cancelled': cancelled_values,
        }

    @staticmethod
    def build_chart_data(top_disrupted_airlines, top_disrupted_routes, current_status_distribution, best_airlines, best_routes):
        airline_labels = [item['flight__airline__name'] for item in top_disrupted_airlines]
        airline_values = [item['total'] for item in top_disrupted_airlines]

        route_labels = [item['route_key'] for item in top_disrupted_routes]
        route_values = [item['total'] for item in top_disrupted_routes]

        status_labels = [item['status'].replace('_', ' ').title() for item in current_status_distribution]
        status_values = [item['total'] for item in current_status_distribution]

        performance_labels = [item['airline_name'] for item in best_airlines]
        performance_values = [item['score'] for item in best_airlines]

        route_stability_labels = [item['route_key'] for item in best_routes]
        route_stability_values = [item['stability_score'] for item in best_routes]

        return {
            'airline_chart_data': {
                'labels': airline_labels,
                'values': airline_values,
            },
            'route_chart_data': {
                'labels': route_labels,
                'values': route_values,
            },
            'status_chart_data': {
                'labels': status_labels,
                'values': status_values,
            },
            'performance_chart_data': {
                'labels': performance_labels,
                'values': performance_values,
            },
            'route_stability_chart_data': {
                'labels': route_stability_labels,
                'values': route_stability_values,
            },
        }

    @staticmethod
    def build_insights_and_recommendations(
        filtered_airline_stats,
        route_stats,
        top_disrupted_airlines,
        top_disrupted_routes,
        cancelled_history_count,
        delayed_history_count,
        total_history_records,
        current_delay_rate,
        current_cancellation_rate,
        operational_score
    ):
        analytics_insights = []
        ai_recommendations = []

        total_delays = sum(item['delays'] for item in filtered_airline_stats)
        total_cancellations = sum(item['cancellations'] for item in filtered_airline_stats)
        total_records = sum(item['total'] for item in filtered_airline_stats)

        best_airline = None
        worst_airline = None
        best_route = None
        worst_route = None

        if top_disrupted_airlines:
            analytics_insights.append(
                f"{top_disrupted_airlines[0]['flight__airline__name']} is the most disrupted airline based on historical records."
            )

        if top_disrupted_routes:
            analytics_insights.append(
                f"{top_disrupted_routes[0]['route_key']} is the most disrupted route."
            )

        if cancelled_history_count > 0:
            analytics_insights.append(
                "Cancelled flight history exists and should be reviewed as high-priority operational anomalies."
            )

        analytics_insights.append(
            f"Current operational delay rate is {current_delay_rate}% and current cancellation rate is {current_cancellation_rate}%."
        )

        analytics_insights.append(
            f"Global operational score is currently {operational_score}% based on active current flight conditions."
        )

        if filtered_airline_stats:
            best_airline = max(filtered_airline_stats, key=lambda x: x['score'])
            worst_airline = min(filtered_airline_stats, key=lambda x: x['score'])

            analytics_insights.append(
                f"{best_airline['airline_name']} is currently the most reliable airline with a performance score of {best_airline['score']}%."
            )

            analytics_insights.append(
                f"{worst_airline['airline_name']} shows the lowest reliability level at {worst_airline['score']}%."
            )

            if worst_airline['cancellations'] > 0:
                ai_recommendations.append(
                    f"Critical alert: {worst_airline['airline_name']} has cancellation history. Immediate operational audit is recommended."
                )

            if worst_airline['score'] < 70:
                ai_recommendations.append(
                    f"Monitor {worst_airline['airline_name']} closely because its performance score is critically low."
                )

            if best_airline['total'] > 10 and best_airline['score'] > 90:
                ai_recommendations.append(
                    f"{best_airline['airline_name']} demonstrates high reliability at scale and can be prioritized for strategic operations."
                )
            elif best_airline['score'] > 90:
                ai_recommendations.append(
                    f"{best_airline['airline_name']} can be prioritized for stable and high-confidence operations."
                )

        if route_stats:
            best_route = max(route_stats, key=lambda x: x['stability_score'])
            worst_route = min(route_stats, key=lambda x: x['stability_score'])

            analytics_insights.append(
                f"{best_route['route_key']} is the most stable route with a route stability score of {best_route['stability_score']}%."
            )

            analytics_insights.append(
                f"{worst_route['route_key']} is the weakest route with a route stability score of {worst_route['stability_score']}%."
            )

            if worst_route['stability_score'] < 70:
                ai_recommendations.append(
                    f"Route {worst_route['route_key']} requires reinforced supervision because its stability score is critically low."
                )

        if top_disrupted_routes:
            top_route = top_disrupted_routes[0]
            ai_recommendations.append(
                f"Avoid or closely supervise route {top_route['route_key']} because it currently has the highest disruption concentration."
            )

        for airline in filtered_airline_stats:
            if airline['anomaly']:
                ai_recommendations.append(airline['anomaly_message'])

        if total_cancellations > 0:
            ai_recommendations.append(
                "Flight cancellations have been detected. Manual operational review is recommended for affected airlines and routes."
            )

        if total_delays == 0 and total_cancellations == 0:
            ai_recommendations.append(
                "No disruptions are currently detected. Verify that the historical dataset is sufficiently rich before drawing strong conclusions."
            )

        if total_records < 50:
            ai_recommendations.append(
                "Historical data volume remains limited. Continue collecting flight events to improve analytical confidence."
            )
        elif total_records > 200:
            ai_recommendations.append(
                "The historical dataset is large enough to support stronger performance interpretation and ranking decisions."
            )

        if delayed_history_count == 0 and cancelled_history_count <= 3 and total_history_records > 0:
            analytics_insights.append(
                "The current dataset contains very few disruption events, so performance scores are influenced strongly by historical volume confidence."
            )

        if total_history_records == 0:
            analytics_insights.append(
                "No historical records available yet. Run a backfill and continue syncing flights to build analytics."
            )

        return {
            'analytics_insights': analytics_insights,
            'ai_recommendations': ai_recommendations,
            'best_airline': best_airline,
            'worst_airline': worst_airline,
            'best_route': best_route,
            'worst_route': worst_route,
        }

    @staticmethod
    def build_predictions(filtered_airline_stats, route_stats):
        predictions = []

        flights_for_prediction = Flight.objects.select_related(
            'airline',
            'origin_airport',
            'destination_airport'
        ).order_by('-scheduled_departure')[:10]

        for flight in flights_for_prediction:
            route_key = f"{flight.origin_airport.iata_code} → {flight.destination_airport.iata_code}"

            risk = AnalyticsService.calculate_delay_risk(
                filtered_airline_stats,
                route_stats,
                flight.airline.name if flight.airline else None,
                route_key
            )

            if risk >= 70:
                level = 'High Risk'
                badge_class = 'risk-high'
            elif risk >= 40:
                level = 'Moderate Risk'
                badge_class = 'risk-medium'
            else:
                level = 'Low Risk'
                badge_class = 'risk-low'

            predictions.append({
                'flight_number': flight.flight_number,
                'route': route_key,
                'airline': flight.airline.name if flight.airline else 'Unknown',
                'risk': risk,
                'level': level,
                'badge_class': badge_class,
                'status': flight.get_status_display(),
                'source_type': flight.source_type,
            })

        return predictions

    @staticmethod
    def build_current_operational_kpis():
        total_flights = Flight.objects.count()
        delayed_count = Flight.objects.filter(status='delayed').count()
        cancelled_count = Flight.objects.filter(status='cancelled').count()
        active_count = Flight.objects.exclude(status__in=['landed', 'cancelled']).count()

        current_delay_rate = round((delayed_count / total_flights) * 100, 1) if total_flights else 0
        current_cancellation_rate = round((cancelled_count / total_flights) * 100, 1) if total_flights else 0
        active_rate = round((active_count / total_flights) * 100, 1) if total_flights else 0

        clean_operations = total_flights - delayed_count - cancelled_count
        operational_score = round((clean_operations / total_flights) * 100, 1) if total_flights else 0

        return {
            'total_flights': total_flights,
            'delayed_count': delayed_count,
            'cancelled_count': cancelled_count,
            'active_count': active_count,
            'current_delay_rate': current_delay_rate,
            'current_cancellation_rate': current_cancellation_rate,
            'active_rate': active_rate,
            'operational_score': operational_score,
        }

    @staticmethod
    def build_analytics_context():
        current_kpis = AnalyticsService.build_current_operational_kpis()

        total_history_records = FlightStatusHistory.objects.count()
        delayed_history_count = FlightStatusHistory.objects.filter(new_status='delayed').count()
        cancelled_history_count = FlightStatusHistory.objects.filter(new_status='cancelled').count()
        in_air_history_count = FlightStatusHistory.objects.filter(new_status='in_air').count()

        top_disrupted_airlines = AnalyticsService.get_top_disrupted_airlines()
        top_disrupted_routes = AnalyticsService.get_top_disrupted_routes()
        daily_disruptions = AnalyticsService.get_daily_disruptions()
        current_status_distribution = AnalyticsService.get_current_status_distribution()
        filtered_airline_stats = AnalyticsService.get_airline_stats()
        route_stats = AnalyticsService.get_route_stats()

        best_airlines = sorted(
            filtered_airline_stats,
            key=lambda x: (-x['score'], -x['total'], x['airline_name'])
        )[:8]

        worst_airlines = sorted(
            filtered_airline_stats,
            key=lambda x: (x['score'], -x['cancellations'], -x['delays'], x['airline_name'])
        )[:5]

        best_routes = sorted(
            route_stats,
            key=lambda x: (-x['stability_score'], -x['total'], x['route_key'])
        )[:8]

        worst_routes = sorted(
            route_stats,
            key=lambda x: (x['stability_score'], -x['critical_events'], x['route_key'])
        )[:5]

        insights_bundle = AnalyticsService.build_insights_and_recommendations(
            filtered_airline_stats=filtered_airline_stats,
            route_stats=route_stats,
            top_disrupted_airlines=top_disrupted_airlines,
            top_disrupted_routes=top_disrupted_routes,
            cancelled_history_count=cancelled_history_count,
            delayed_history_count=delayed_history_count,
            total_history_records=total_history_records,
            current_delay_rate=current_kpis['current_delay_rate'],
            current_cancellation_rate=current_kpis['current_cancellation_rate'],
            operational_score=current_kpis['operational_score'],
        )

        predictions = AnalyticsService.build_predictions(
            filtered_airline_stats=filtered_airline_stats,
            route_stats=route_stats,
        )

        chart_bundle = AnalyticsService.build_chart_data(
            top_disrupted_airlines=top_disrupted_airlines,
            top_disrupted_routes=top_disrupted_routes,
            current_status_distribution=current_status_distribution,
            best_airlines=best_airlines,
            best_routes=best_routes,
        )

        trend_chart_data = AnalyticsService.build_trend_chart_data(daily_disruptions)

        return {
            **current_kpis,
            'total_history_records': total_history_records,
            'delayed_history_count': delayed_history_count,
            'cancelled_history_count': cancelled_history_count,
            'in_air_history_count': in_air_history_count,
            'analytics_insights': insights_bundle['analytics_insights'],
            'ai_recommendations': insights_bundle['ai_recommendations'],
            'predictions': predictions,
            'trend_chart_data': trend_chart_data,
            'top_disrupted_airlines': top_disrupted_airlines,
            'top_disrupted_routes': top_disrupted_routes,
            'best_airlines': best_airlines,
            'worst_airlines': worst_airlines,
            'best_routes': best_routes,
            'worst_routes': worst_routes,
            **chart_bundle,
        }