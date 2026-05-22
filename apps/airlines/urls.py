from django.urls import path

from .views import airline_detail, airline_list


app_name = 'airlines'

urlpatterns = [
    path('', airline_list, name='airline_list'),
    path('<int:pk>/', airline_detail, name='airline_detail'),
]