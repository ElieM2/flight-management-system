from django.urls import path
from .views import sync_page

app_name = 'integrations'
urlpatterns = [
    path('', sync_page, name='sync_page'),
]