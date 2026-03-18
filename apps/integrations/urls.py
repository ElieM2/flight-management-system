from django.urls import path
from .views import sync_page

urlpatterns = [
    path('', sync_page, name='sync_page'),
]