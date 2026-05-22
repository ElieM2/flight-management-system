from django.urls import path

from .views import (
    analytics_charts,
    analytics_feedback,
    analytics_home,
    analytics_reliability,
    analytics_reports,
    analytics_routes,
)


app_name = 'analytics'

urlpatterns = [
    path('', analytics_home, name='home'),
    path('reports/', analytics_reports, name='reports'),
    path('charts/', analytics_charts, name='charts'),
    path('routes/', analytics_routes, name='routes'),
    path('reliability/', analytics_reliability, name='reliability'),
    path('feedback/', analytics_feedback, name='feedback'),
]