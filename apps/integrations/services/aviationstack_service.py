import os
import re
import requests


class AviationstackService:
    def __init__(self):
        self.api_key = os.getenv('AVIATIONSTACK_API_KEY')
        self.base_url = os.getenv(
            'AVIATIONSTACK_BASE_URL',
            'https://api.aviationstack.com/v1'
        ).rstrip('/')

        if not self.api_key:
            raise RuntimeError("AVIATIONSTACK_API_KEY is missing in environment variables.")

        self.session = requests.Session()

    def _sanitize_text(self, value):
        if not value:
            return value

        text = str(value)

        if self.api_key:
            text = text.replace(self.api_key, '***REDACTED_API_KEY***')

        text = re.sub(
            r'(access_key=)([^&\s]+)',
            r'\1***REDACTED_API_KEY***',
            text,
            flags=re.IGNORECASE
        )
        return text

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

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            safe_details = self._sanitize_text(str(exc))

            if status_code == 401:
                raise RuntimeError(
                    "Aviationstack authentication failed. Check the API key."
                ) from exc

            if status_code == 403:
                raise RuntimeError(
                    "Aviationstack access was denied. Check plan permissions, endpoint access, and HTTPS base URL."
                ) from exc

            if status_code == 429:
                raise RuntimeError(
                    "Aviationstack rate or usage limit has been reached."
                ) from exc

            raise RuntimeError(
                f"Aviationstack request failed: {safe_details}"
            ) from exc

        except requests.RequestException as exc:
            safe_details = self._sanitize_text(str(exc))
            raise RuntimeError(
                f"Aviationstack network request failed: {safe_details}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError("Aviationstack returned invalid JSON.") from exc

        if payload.get('error'):
            error_info = payload['error']
            code = error_info.get('code', 'unknown_error')
            message = error_info.get('message') or str(error_info)
            safe_message = self._sanitize_text(message)

            if code in {'invalid_access_key', 'missing_access_key', 'inactive_user'}:
                raise RuntimeError(
                    f"Aviationstack authentication error: {safe_message}"
                )

            if code in {'https_access_restricted', 'function_access_restricted'}:
                raise RuntimeError(
                    f"Aviationstack access restriction: {safe_message}"
                )

            if code in {'usage_limit_reached', 'rate_limit_reached'}:
                raise RuntimeError(
                    f"Aviationstack quota error: {safe_message}"
                )

            raise RuntimeError(f"Aviationstack API error: {safe_message}")

        if 'data' not in payload:
            raise RuntimeError("Aviationstack response does not contain a 'data' field.")

        return payload