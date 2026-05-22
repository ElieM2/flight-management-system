import math
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
from django.core.cache import cache
from django.utils import timezone


@dataclass
class AirportWeatherPoint:
    code: str
    city: str
    lat: float
    lng: float


class WeatherHazardService:
    """
    Weather and hazards service for the operational flight map.

    Sources:
    - RainViewer: real precipitation radar tile metadata.
    - Open-Meteo: current airport-level weather indicators.
    - Local flight state: delayed, cancelled, high-risk operational pressure.

    This service is intentionally cached because the map can refresh often.
    """

    RAINVIEWER_URL = "https://api.rainviewer.com/public/weather-maps.json"
    OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

    RAINVIEWER_CACHE_KEY = "logosflight:weather:rainviewer:latest"
    AIRPORT_WEATHER_CACHE_PREFIX = "logosflight:weather:openmeteo:airport"

    RAINVIEWER_CACHE_SECONDS = 10 * 60
    AIRPORT_WEATHER_CACHE_SECONDS = 12 * 60
    ERROR_CACHE_SECONDS = 60

    REQUEST_TIMEOUT = 10

    HEADERS = {
        "User-Agent": (
            "LogosFlightDiplomaProject/1.0 "
            "(Django operational flight monitoring; educational use)"
        ),
        "Accept": "application/json,text/plain,*/*",
    }

    @classmethod
    def build_weather_payload(
        cls,
        airports: List[Dict[str, Any]],
        operational_summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        clean_airports = cls._clean_airports(airports)

        radar = cls.get_latest_rainviewer_radar()
        weather_records = cls.get_airport_weather_records(clean_airports)

        summary = cls._build_summary(
            weather_records=weather_records,
            operational_summary=operational_summary or {},
        )

        return {
            "ok": True,
            "source": "Django cache · RainViewer · Open-Meteo",
            "generated_at": timezone.now().isoformat(),
            "radar": radar,
            "summary": summary,
            "hazards": weather_records,
        }

    @classmethod
    def get_latest_rainviewer_radar(cls) -> Dict[str, Any]:
        cached = cache.get(cls.RAINVIEWER_CACHE_KEY)

        if cached:
            return cached

        try:
            response = requests.get(
                cls.RAINVIEWER_URL,
                headers=cls.HEADERS,
                timeout=cls.REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            payload = response.json()

            host = payload.get("host")
            radar = payload.get("radar") or {}
            past_frames = radar.get("past") or []
            nowcast_frames = radar.get("nowcast") or []

            frames = past_frames + nowcast_frames
            latest = frames[-1] if frames else None

            if not host or not latest or not latest.get("path"):
                result = cls._radar_unavailable(
                    message="No RainViewer radar frame was available in the API response.",
                    host=host,
                )
                cache.set(cls.RAINVIEWER_CACHE_KEY, result, cls.ERROR_CACHE_SECONDS)
                return result

            tile_url = f"{host}{latest['path']}/256/{{z}}/{{x}}/{{y}}/2/1_1.png"

            result = {
                "available": True,
                "status": "active",
                "message": "Real precipitation radar available.",
                "provider": "RainViewer",
                "host": host,
                "path": latest.get("path"),
                "time": latest.get("time"),
                "tile_url": tile_url,
                "updated_at": cls._format_unix_utc(latest.get("time")),
            }

            cache.set(cls.RAINVIEWER_CACHE_KEY, result, cls.RAINVIEWER_CACHE_SECONDS)
            return result

        except requests.RequestException as exc:
            result = cls._radar_unavailable(
                message=f"RainViewer request failed: {exc}",
                host=None,
            )
            cache.set(cls.RAINVIEWER_CACHE_KEY, result, cls.ERROR_CACHE_SECONDS)
            return result

        except ValueError as exc:
            result = cls._radar_unavailable(
                message=f"RainViewer returned invalid JSON: {exc}",
                host=None,
            )
            cache.set(cls.RAINVIEWER_CACHE_KEY, result, cls.ERROR_CACHE_SECONDS)
            return result

        except Exception as exc:
            result = cls._radar_unavailable(
                message=f"Unexpected RainViewer error: {exc}",
                host=None,
            )
            cache.set(cls.RAINVIEWER_CACHE_KEY, result, cls.ERROR_CACHE_SECONDS)
            return result

    @classmethod
    def _radar_unavailable(cls, message: str, host: Optional[str]) -> Dict[str, Any]:
        return {
            "available": False,
            "status": "standby",
            "message": message,
            "provider": "RainViewer",
            "host": host,
            "path": None,
            "time": None,
            "tile_url": None,
            "updated_at": None,
        }

    @classmethod
    def get_airport_weather_records(
        cls,
        airports: List[AirportWeatherPoint],
    ) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []

        for airport in airports[:8]:
            record = cls.get_airport_weather(airport)

            if record:
                records.append(record)

        return records

    @classmethod
    def get_airport_weather(
        cls,
        airport: AirportWeatherPoint,
    ) -> Optional[Dict[str, Any]]:
        cache_key = (
            f"{cls.AIRPORT_WEATHER_CACHE_PREFIX}:"
            f"{airport.code}:{round(airport.lat, 2)}:{round(airport.lng, 2)}"
        )

        cached = cache.get(cache_key)

        if cached:
            return cached

        params = {
            "latitude": airport.lat,
            "longitude": airport.lng,
            "current": ",".join(
                [
                    "precipitation",
                    "rain",
                    "showers",
                    "snowfall",
                    "weather_code",
                    "wind_speed_10m",
                    "wind_gusts_10m",
                    "visibility",
                ]
            ),
            "wind_speed_unit": "kmh",
            "timezone": "UTC",
        }

        try:
            response = requests.get(
                cls.OPEN_METEO_URL,
                params=params,
                headers=cls.HEADERS,
                timeout=cls.REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            payload = response.json()
            current = payload.get("current") or {}

            record = cls._classify_airport_weather(airport, current)

            cache.set(cache_key, record, cls.AIRPORT_WEATHER_CACHE_SECONDS)
            return record

        except Exception:
            return None

    @classmethod
    def _classify_airport_weather(
        cls,
        airport: AirportWeatherPoint,
        current: Dict[str, Any],
    ) -> Dict[str, Any]:
        precipitation = cls._to_float(current.get("precipitation"), 0.0)
        rain = cls._to_float(current.get("rain"), 0.0)
        showers = cls._to_float(current.get("showers"), 0.0)
        snowfall = cls._to_float(current.get("snowfall"), 0.0)

        weather_code = cls._to_int(current.get("weather_code"))
        wind_speed = cls._to_float(current.get("wind_speed_10m"), 0.0)
        wind_gusts = cls._to_float(current.get("wind_gusts_10m"), 0.0)
        visibility = cls._to_float(current.get("visibility"), None)

        wet_amount = precipitation + rain + showers
        gust_gap = max(0.0, wind_gusts - wind_speed)

        has_rain = wet_amount > 0.2 or cls._is_rain_weather_code(weather_code)
        has_storm = (
            cls._is_storm_weather_code(weather_code)
            or wet_amount >= 7.0
            or wind_gusts >= 55.0
        )
        has_snow = snowfall > 0.1 or cls._is_snow_weather_code(weather_code)
        has_turbulence = (
            wind_gusts >= 45.0
            or wind_speed >= 35.0
            or gust_gap >= 18.0
        )
        low_visibility = visibility is not None and 0 < visibility < 6000

        severity = "low"

        if has_storm or wind_gusts >= 60.0 or wet_amount >= 8.0:
            severity = "high"
        elif has_turbulence or has_rain or has_snow or low_visibility:
            severity = "medium"

        return {
            "airport": airport.code,
            "city": airport.city,
            "lat": airport.lat,
            "lng": airport.lng,
            "updated_at": current.get("time"),
            "weather_code": weather_code,
            "precipitation": round(wet_amount, 1),
            "snowfall": round(snowfall, 1),
            "wind_speed": round(wind_speed),
            "wind_gusts": round(wind_gusts),
            "visibility": round(visibility) if visibility is not None else None,
            "rain": has_rain,
            "storm": has_storm,
            "snow": has_snow,
            "turbulence": has_turbulence,
            "low_visibility": low_visibility,
            "severity": severity,
            "source": "Open-Meteo",
        }

    @classmethod
    def _build_summary(
        cls,
        weather_records: List[Dict[str, Any]],
        operational_summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        rain_records = sum(1 for record in weather_records if record.get("rain"))
        storm_records = sum(1 for record in weather_records if record.get("storm"))
        turbulence_records = sum(1 for record in weather_records if record.get("turbulence"))

        visibility_records = sum(
            1
            for record in weather_records
            if record.get("snow") or record.get("low_visibility")
        )

        return {
            "rain_records": rain_records,
            "storm_records": storm_records,
            "turbulence_records": turbulence_records,
            "visibility_records": visibility_records,
            "delayed": int(operational_summary.get("delayed", 0) or 0),
            "cancelled": int(operational_summary.get("cancelled", 0) or 0),
            "high_risk": int(operational_summary.get("high_risk", 0) or 0),
            "visible_flights": int(operational_summary.get("visible_flights", 0) or 0),
        }

    @classmethod
    def _clean_airports(
        cls,
        airports: List[Dict[str, Any]],
    ) -> List[AirportWeatherPoint]:
        clean: List[AirportWeatherPoint] = []
        seen = set()

        for item in airports:
            code = str(item.get("code") or "").strip().upper()
            city = str(item.get("city") or "").strip()
            lat = cls._to_float(item.get("lat"), None)
            lng = cls._to_float(item.get("lng"), None)

            if not code or code in seen:
                continue

            if lat is None or lng is None:
                continue

            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                continue

            seen.add(code)

            clean.append(
                AirportWeatherPoint(
                    code=code,
                    city=city,
                    lat=lat,
                    lng=lng,
                )
            )

        return clean[:8]

    @staticmethod
    def _is_storm_weather_code(code: Optional[int]) -> bool:
        return code in {95, 96, 99}

    @staticmethod
    def _is_rain_weather_code(code: Optional[int]) -> bool:
        return code in {
            51,
            53,
            55,
            56,
            57,
            61,
            63,
            65,
            66,
            67,
            80,
            81,
            82,
        }

    @staticmethod
    def _is_snow_weather_code(code: Optional[int]) -> bool:
        return code in {71, 73, 75, 77, 85, 86}

    @staticmethod
    def _to_float(value: Any, default: Optional[float] = 0.0) -> Optional[float]:
        try:
            if value is None:
                return default

            number = float(value)

            if math.isnan(number) or math.isinf(number):
                return default

            return number

        except Exception:
            return default

    @staticmethod
    def _to_int(value: Any) -> Optional[int]:
        try:
            if value is None:
                return None

            return int(value)

        except Exception:
            return None

    @staticmethod
    def _format_unix_utc(value: Any) -> Optional[str]:
        try:
            timestamp = int(value)
            return time.strftime("%H:%M UTC", time.gmtime(timestamp))

        except Exception:
            return None