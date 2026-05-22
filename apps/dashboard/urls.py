from django.urls import path
from .views import public_home_view, private_dashboard_view

app_name = 'dashboard'

urlpatterns = [
    path('', public_home_view, name='home'),
    path('dashboard/', private_dashboard_view, name='dashboard'),
]