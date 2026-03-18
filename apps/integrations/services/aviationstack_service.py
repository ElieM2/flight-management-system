import os
import requests


class AviationstackService:
    def __init__(self):
        self.api_key = os.getenv('AVIATIONSTACK_API_KEY')
        self.base_url = os.getenv('AVIATIONSTACK_BASE_URL', 'http://api.aviationstack.com/v1')

    def get_flights(self, flight_iata=None, dep_iata=None, arr_iata=None, limit=20):
        url = f"{self.base_url}/flights"
        params = {
            'access_key': self.api_key,
            'limit': limit,
        }

        if flight_iata:
            params['flight_iata'] = flight_iata
        if dep_iata:
            params['dep_iata'] = dep_iata
        if arr_iata:
            params['arr_iata'] = arr_iata

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()