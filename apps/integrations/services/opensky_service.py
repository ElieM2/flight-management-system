import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests
from django.conf import settings
from django.db import transaction

from apps.flights.models import Flight, FlightStatusHistory

logger = logging.getLogger(__name__)

OPEN_SKY_TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
)
OPEN_SKY_STATES_ALL_URL = "https://opensky-network.org/api/states/all"


@dataclass
class OpenSkyState:
    icao24: str
    callsign: Optional[str]
    origin_country: Optional[str]
    time_position: Optional[float]
    last_contact: Optional[float]
    longitude: Optional[float]
    latitude: Optional[float]
    baro_altitude: Optional[float]
    on_ground: Optional[bool]
    velocity: Optional[float]
    true_track: Optional[float]
    vertical_rate: Optional[float]
    geo_altitude: Optional[float]
    squawk: Optional[str]
    spi: Optional[bool]
    position_source: Optional[int]

    @classmethod
    def from_raw(cls, raw: List[Any]) -> "OpenSkyState":
        return cls(
            icao24=(raw[0] or "").strip().lower(),
            callsign=(raw[1] or "").strip() if raw[1] else None,
            origin_country=raw[2],
            time_position=raw[3],
            last_contact=raw[4],
            longitude=raw[5],
            latitude=raw[6],
            baro_altitude=raw[7],
            on_ground=raw[8],
            velocity=raw[9],
            true_track=raw[10],
            vertical_rate=raw[11],
            geo_altitude=raw[13],
            squawk=raw[14],
            spi=raw[15],
            position_source=raw[16],
        )


class OpenSkyServiceError(Exception):
    pass


class OpenSkyService:
    def __init__(self) -> None:
        self.client_id = getattr(settings, "OPENSKY_CLIENT_ID", "").strip()
        self.client_secret = getattr(settings, "OPENSKY_CLIENT_SECRET", "").strip()
        self.timeout = getattr(settings, "OPENSKY_TIMEOUT", 20)
        self.region = getattr(settings, "OPENSKY_REGION", {})
        self.session = requests.Session()

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _get_access_token(self) -> str:
        if not self.is_configured():
            raise OpenSkyServiceError(
                "OpenSky credentials are missing. Configure OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET."
            )

        response = self.session.post(
            OPEN_SKY_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=self.timeout,
        )

        if response.status_code != 200:
            raise OpenSkyServiceError(
                f"Failed to obtain OpenSky access token. Status={response.status_code}, body={response.text}"
            )

        data = response.json()
        token = data.get("access_token")
        if not token:
            raise OpenSkyServiceError("OpenSky token response did not contain access_token.")

        return token

    def fetch_states(self) -> List[OpenSkyState]:
        token = self._get_access_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        params: Dict[str, Any] = {}

        lamin = self.region.get("lamin")
        lomin = self.region.get("lomin")
        lamax = self.region.get("lamax")
        lomax = self.region.get("lomax")

        if None not in (lamin, lomin, lamax, lomax):
            params.update(
                {
                    "lamin": lamin,
                    "lomin": lomin,
                    "lamax": lamax,
                    "lomax": lomax,
                }
            )

        response = self.session.get(
            OPEN_SKY_STATES_ALL_URL,
            headers=headers,
            params=params,
            timeout=self.timeout,
        )

        if response.status_code != 200:
            raise OpenSkyServiceError(
                f"Failed to fetch OpenSky states. Status={response.status_code}, body={response.text}"
            )

        payload = response.json()
        raw_states = payload.get("states") or []

        states: List[OpenSkyState] = []
        for raw in raw_states:
            try:
                state = OpenSkyState.from_raw(raw)
                if state.latitude is None or state.longitude is None:
                    continue
                states.append(state)
            except Exception as exc:
                logger.warning("Skipping invalid OpenSky state row: %s | error=%s", raw, exc)

        return states

    @staticmethod
    def _normalize_callsign(value: Optional[str]) -> str:
        if not value:
            return ""
        return "".join(value.upper().split())

    @staticmethod
    def _extract_numeric_suffix(value: Optional[str]) -> str:
        if not value:
            return ""
        return "".join(ch for ch in value if ch.isdigit())

    def _index_states(self, states: List[OpenSkyState]) -> Dict[str, OpenSkyState]:
        indexed: Dict[str, OpenSkyState] = {}

        for state in states:
            if state.callsign:
                normalized = self._normalize_callsign(state.callsign)
                if normalized and normalized not in indexed:
                    indexed[normalized] = state

        return indexed

    def _build_flight_queryset(self):
        return Flight.objects.select_related(
            "airline",
            "origin_airport",
            "destination_airport",
            "aircraft",
        ).prefetch_related("status_history")

    def _create_live_history_entry(
        self,
        flight: Flight,
        previous_status: str,
        summary: str,
    ) -> None:
        FlightStatusHistory.objects.create(
            flight=flight,
            previous_status=previous_status,
            new_status=flight.status,
            change_type="live",
            source_type_snapshot=flight.source_type,
            scheduled_departure_snapshot=flight.scheduled_departure,
            scheduled_arrival_snapshot=flight.scheduled_arrival,
            actual_departure_snapshot=flight.actual_departure,
            actual_arrival_snapshot=flight.actual_arrival,
            departure_delay_minutes=flight.get_departure_delay_minutes(),
            arrival_delay_minutes=flight.get_arrival_delay_minutes(),
            is_disruption_event=flight.has_disruption(),
            status_changed=(previous_status != flight.status),
            schedule_changed=False,
            live_data_changed=True,
            change_summary=summary,
            changed_by=None,
        )

    def _apply_state_to_flight(self, flight: Flight, state: OpenSkyState, strategy: str) -> bool:
        changed = False
        previous_status = flight.status

        new_latitude = float(state.latitude) if state.latitude is not None else None
        new_longitude = float(state.longitude) if state.longitude is not None else None
        new_altitude = (
            float(state.geo_altitude or state.baro_altitude)
            if (state.geo_altitude is not None or state.baro_altitude is not None)
            else None
        )
        new_speed_kmh = float(state.velocity * 3.6) if state.velocity is not None else None
        new_direction = float(state.true_track) if state.true_track is not None else None

        if flight.live_latitude != new_latitude:
            flight.live_latitude = new_latitude
            changed = True

        if flight.live_longitude != new_longitude:
            flight.live_longitude = new_longitude
            changed = True

        if flight.live_altitude != new_altitude:
            flight.live_altitude = new_altitude
            changed = True

        if flight.live_speed != new_speed_kmh:
            flight.live_speed = new_speed_kmh
            changed = True

        if flight.live_direction != new_direction:
            flight.live_direction = new_direction
            changed = True

        if flight.external_id != state.icao24:
            flight.external_id = state.icao24
            changed = True

        if flight.status not in ["cancelled", "landed"]:
            if state.on_ground is False and flight.status in ["scheduled", "boarding", "departed"]:
                flight.status = "in_air"
                changed = True
            elif state.on_ground is True and flight.status == "scheduled":
                flight.status = "boarding"
                changed = True

        if not changed:
            return False

        flight.save(
            update_fields=[
                "live_latitude",
                "live_longitude",
                "live_altitude",
                "live_speed",
                "live_direction",
                "external_id",
                "status",
                "updated_at",
            ]
        )

        summary = (
            f"OpenSky live update applied"
            f" | strategy={strategy}"
            f" | callsign={state.callsign or '-'}"
            f" | icao24={state.icao24}"
        )
        self._create_live_history_entry(
            flight=flight,
            previous_status=previous_status,
            summary=summary,
        )
        return True

    def _try_match_state(
        self,
        flight: Flight,
        indexed_states: Dict[str, OpenSkyState],
        states: List[OpenSkyState],
        active_flights: List[Flight],
    ) -> Tuple[Optional[OpenSkyState], Optional[str], Optional[str]]:
        normalized_flight_number = self._normalize_callsign(flight.flight_number)

        exact_state = indexed_states.get(normalized_flight_number)
        if exact_state:
            return exact_state, "exact_callsign", "high"

        if flight.external_id:
            target_icao24 = str(flight.external_id).strip().lower()
            for candidate in states:
                if candidate.icao24 == target_icao24:
                    return candidate, "external_id", "high"

        flight_digits = self._extract_numeric_suffix(flight.flight_number)
        if not flight_digits:
            return None, None, None

        same_digits_flights = [
            item for item in active_flights
            if self._extract_numeric_suffix(item.flight_number) == flight_digits
        ]

        if len(same_digits_flights) != 1:
            return None, None, None

        candidate_states = []
        for state in states:
            if self._extract_numeric_suffix(state.callsign) == flight_digits:
                candidate_states.append(state)

        if len(candidate_states) == 1:
            return candidate_states[0], "numeric_suffix", "low"

        return None, None, None

    def build_diagnostics(self, states: List[OpenSkyState], flights) -> Dict[str, Any]:
        opensky_callsigns = sorted(
            {
                self._normalize_callsign(state.callsign)
                for state in states
                if state.callsign
            }
        )

        local_flight_numbers = sorted(
            {
                self._normalize_callsign(flight.flight_number)
                for flight in flights
                if flight.flight_number
            }
        )

        local_digits = sorted(
            {
                self._extract_numeric_suffix(flight.flight_number)
                for flight in flights
                if self._extract_numeric_suffix(flight.flight_number)
            }
        )

        opensky_digits = sorted(
            {
                self._extract_numeric_suffix(state.callsign)
                for state in states
                if self._extract_numeric_suffix(state.callsign)
            }
        )

        common_exact = sorted(set(local_flight_numbers) & set(opensky_callsigns))
        common_digits = sorted(set(local_digits) & set(opensky_digits))

        return {
            "sample_opensky_callsigns": opensky_callsigns[:40],
            "sample_local_flights": local_flight_numbers[:40],
            "common_exact": common_exact[:40],
            "common_digits": common_digits[:40],
        }

    @transaction.atomic
    def sync_live_states(self) -> Dict[str, Any]:
        states = self.fetch_states()
        indexed_states = self._index_states(states)

        flights_qs = self._build_flight_queryset().filter(
            status__in=["scheduled", "boarding", "departed", "in_air"]
        )
        flights = list(flights_qs)

        updated_count = 0
        matched_count = 0
        unmatched_flights: List[str] = []
        matched_details: List[Dict[str, str]] = []

        for flight in flights:
            state, strategy, confidence = self._try_match_state(
                flight=flight,
                indexed_states=indexed_states,
                states=states,
                active_flights=flights,
            )

            if not state:
                unmatched_flights.append(flight.flight_number)
                continue

            matched_count += 1

            matched_details.append(
                {
                    "flight_number": flight.flight_number,
                    "callsign": state.callsign or "-",
                    "icao24": state.icao24,
                    "strategy": strategy or "-",
                    "confidence": confidence or "-",
                }
            )

            try:
                changed = self._apply_state_to_flight(flight, state, strategy or "unknown")
                if changed:
                    updated_count += 1
            except Exception as exc:
                logger.exception(
                    "Failed to apply OpenSky state to flight %s: %s",
                    flight.flight_number,
                    exc,
                )

        diagnostics = self.build_diagnostics(states, flights)

        return {
            "success": True,
            "states_received": len(states),
            "matched_flights": matched_count,
            "updated_flights": updated_count,
            "unmatched_flights": unmatched_flights,
            "matched_details": matched_details,
            "diagnostics": diagnostics,
        }