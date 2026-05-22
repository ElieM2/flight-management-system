import os
import re
import requests


class AirLabsService:
    def __init__(self):
        self.api_key = os.getenv('AIRLABS_API_KEY')
        self.base_url = os.getenv(
            'AIRLABS_BASE_URL',
            'https://airlabs.co/api/v9'
        ).rstrip('/')

        if not self.api_key:
            raise RuntimeError("AIRLABS_API_KEY is missing in environment variables.")

        self.session = requests.Session()

    def _sanitize_text(self, value):
        if not value:
            return value

        text = str(value)

        if self.api_key:
            text = text.replace(self.api_key, '***REDACTED_API_KEY***')

        text = re.sub(
            r'([?&]api_key=)([^&\s]+)',
            r'\1***REDACTED_API_KEY***',
            text,
            flags=re.IGNORECASE
        )
        return text

    def _request(self, endpoint, params=None):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        request_params = {
            'api_key': self.api_key,
        }

        if params:
            request_params.update(params)

        try:
            response = self.session.get(url, params=request_params, timeout=30)
            response.raise_for_status()
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            safe_details = self._sanitize_text(str(exc))

            if status_code == 401:
                raise RuntimeError(
                    "AirLabs authentication failed. Check the API key."
                ) from exc

            if status_code == 403:
                raise RuntimeError(
                    "AirLabs access was denied. Check plan permissions."
                ) from exc

            if status_code == 429:
                raise RuntimeError(
                    "AirLabs rate or usage limit has been reached."
                ) from exc

            raise RuntimeError(
                f"AirLabs request failed: {safe_details}"
            ) from exc

        except requests.RequestException as exc:
            safe_details = self._sanitize_text(str(exc))
            raise RuntimeError(
                f"AirLabs network request failed: {safe_details}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError("AirLabs returned invalid JSON.") from exc

        if payload.get('error'):
            safe_message = self._sanitize_text(payload.get('message') or str(payload['error']))
            raise RuntimeError(f"AirLabs API error: {safe_message}")

        return payload

    def get_airport_by_iata(self, iata_code):
        if not iata_code:
            raise ValueError("iata_code is required.")

        payload = self._request(
            'airports',
            params={
                'iata_code': iata_code,
                '_fields': 'name,iata_code,icao_code,city,city_code,country_code,lat,lng',
            }
        )

        response_data = payload.get('response') or []
        if not response_data:
            return None

        return response_data[0]

    def get_airport_by_icao(self, icao_code):
        if not icao_code:
            raise ValueError("icao_code is required.")

        payload = self._request(
            'airports',
            params={
                'icao_code': icao_code,
                '_fields': 'name,iata_code,icao_code,city,city_code,country_code,lat,lng',
            }
        )

        response_data = payload.get('response') or []
        if not response_data:
            return None

        return response_data[0]