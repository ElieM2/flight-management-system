from django.urls import path
from .views import airport_detail, airport_list


app_name = 'airports'

urlpatterns = [
    path('', airport_list, name='airport_list'),
    path('<int:pk>/', airport_detail, name='airport_detail'),
]