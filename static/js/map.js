/* Operational flight map */

document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    const WEATHER_ENDPOINT = "/monitoring/api/weather-hazards/";

    const DEFAULT_CENTER = [51.505, 10.0];
    const DEFAULT_ZOOM = 4.5;
    const MIN_ZOOM = 2;
    const MAX_ZOOM = 18;

    const ROUTE_DISPLAY_LIMIT = 45;
    const CRITICAL_ROUTE_DISPLAY_LIMIT = 25;
    const LABEL_DISPLAY_LIMIT = 28;
    const AIRPORT_LABEL_LIMIT = 12;

    const WEATHER_REFRESH_INTERVAL_MS = 5 * 60 * 1000;
    const RENDER_DEBOUNCE_MS = 80;
    const REFRESH_UI_DELAY_MS = 520;

    const els = {};

    const state = {
        map: null,
        baseLayer: null,
        radarLayer: null,
        radarTileUrl: null,
        radarTimestamp: null,
        radarActive: false,
        userMarker: null,

        selectedFlightId: null,
        searchQuery: "",
        statusFilter: "all",
        baseLayerKey: "dark",
        weatherLayerKey: "radar",

        toolsPanelOpen: false,
        fullscreen: false,
        isRefreshing: false,

        lastWeatherPayload: null,
        lastWeatherRefreshAt: null,

        renderTimer: null,
        weatherTimer: null,
        clockTimer: null,

        estimatedLayerEnabled: false,
        realFlights: [],
        flights: [],
        filteredFlights: [],
        visibleFlights: [],

        markers: {
            aircraft: [],
            routes: [],
            labels: [],
            airports: [],
            restrictedZones: [],
            weather: []
        },

        layers: {
            aircraft: null,
            routes: null,
            labels: null,
            airports: null,
            restrictedZones: null,
            weather: null
        },

        toggles: {
            aircraft: true,
            routes: true,
            airports: true,
            labels: true,
            weather: true,
            restrictedZones: true,
            alertZones: true,
            criticalOnly: false
        }
    };

    const baseLayers = {
        dark: {
            name: "Dark operations",
            url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
            options: {
                attribution: "&copy; OpenStreetMap &copy; CARTO",
                subdomains: "abcd",
                maxZoom: 20
            }
        },
        light: {
            name: "Light operations",
            url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
            options: {
                attribution: "&copy; OpenStreetMap &copy; CARTO",
                subdomains: "abcd",
                maxZoom: 20
            }
        },
        satellite: {
            name: "Satellite",
            url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            options: {
                attribution: "Tiles &copy; Esri",
                maxZoom: 20
            }
        }
    };

    const referenceAirports = [
        { code: "LHR", name: "London Heathrow", city: "London", country: "United Kingdom", lat: 51.4700, lng: -0.4543, hub: true },
        { code: "CDG", name: "Paris Charles de Gaulle", city: "Paris", country: "France", lat: 49.0097, lng: 2.5479, hub: true },
        { code: "FRA", name: "Frankfurt Airport", city: "Frankfurt", country: "Germany", lat: 50.0379, lng: 8.5622, hub: true },
        { code: "WAW", name: "Warsaw Chopin", city: "Warsaw", country: "Poland", lat: 52.1657, lng: 20.9671, hub: true },
        { code: "MSQ", name: "Minsk National", city: "Minsk", country: "Belarus", lat: 53.8825, lng: 28.0307, hub: true },
        { code: "IST", name: "Istanbul Airport", city: "Istanbul", country: "Türkiye", lat: 41.2753, lng: 28.7519, hub: true },
        { code: "DOH", name: "Hamad International", city: "Doha", country: "Qatar", lat: 25.2731, lng: 51.6081, hub: true },
        { code: "DXB", name: "Dubai International", city: "Dubai", country: "United Arab Emirates", lat: 25.2532, lng: 55.3657, hub: true },
        { code: "AMS", name: "Amsterdam Schiphol", city: "Amsterdam", country: "Netherlands", lat: 52.3105, lng: 4.7683, hub: true },
        { code: "BCN", name: "Barcelona El Prat", city: "Barcelona", country: "Spain", lat: 41.2974, lng: 2.0833, hub: false },
        { code: "FCO", name: "Rome Fiumicino", city: "Rome", country: "Italy", lat: 41.8003, lng: 12.2389, hub: false },
        { code: "ATH", name: "Athens International", city: "Athens", country: "Greece", lat: 37.9364, lng: 23.9445, hub: false },
        { code: "LIS", name: "Lisbon Airport", city: "Lisbon", country: "Portugal", lat: 38.7742, lng: -9.1342, hub: false },
        { code: "MAD", name: "Madrid Barajas", city: "Madrid", country: "Spain", lat: 40.4983, lng: -3.5676, hub: true },
        { code: "JFK", name: "John F. Kennedy International", city: "New York", country: "United States", lat: 40.6413, lng: -73.7781, hub: true },
        { code: "GRU", name: "São Paulo Guarulhos", city: "São Paulo", country: "Brazil", lat: -23.4356, lng: -46.4731, hub: true },
        { code: "SIN", name: "Singapore Changi", city: "Singapore", country: "Singapore", lat: 1.3644, lng: 103.9915, hub: true },
        { code: "SYD", name: "Sydney Kingsford Smith", city: "Sydney", country: "Australia", lat: -33.9399, lng: 151.1753, hub: true }
    ];

    const referenceFlightSeeds = [
        ["LF101", "LHR", "CDG", "Airbus A320neo", "in_air", "normal", "low", "clear", 62, 18, 4],
        ["LF204", "CDG", "FRA", "Boeing 737 MAX 8", "delayed", "attention", "medium", "operational", 43, 48, 14],
        ["LF318", "FRA", "WAW", "Airbus A321", "in_air", "normal", "low", "clear", 57, 24, 3],
        ["LF422", "WAW", "MSQ", "Embraer E195-E2", "in_air", "normal", "low", "clear", 51, 22, 3],
        ["LF515", "MSQ", "IST", "Airbus A330-300", "in_air", "active", "medium", "attention", 35, 44, 8],
        ["LF609", "IST", "DOH", "Boeing 787-9", "in_air", "normal", "low", "clear", 47, 31, 4],
        ["LF733", "DOH", "DXB", "Airbus A350-900", "delayed", "warning", "high", "storm", 70, 73, 24],
        ["LF840", "AMS", "BCN", "Airbus A320", "in_air", "normal", "low", "clear", 54, 20, 3],
        ["LF912", "BCN", "FCO", "Boeing 737-800", "in_air", "normal", "low", "clear", 39, 26, 3],
        ["LF1045", "FCO", "ATH", "Airbus A321neo", "in_air", "attention", "medium", "wind", 61, 52, 9],
        ["LF1188", "LIS", "MAD", "Boeing 777-300ER", "in_air", "normal", "low", "clear", 73, 17, 2],
        ["LF1201", "MAD", "JFK", "Airbus A350-1000", "in_air", "active", "medium", "attention", 44, 46, 8],
        ["LF1307", "GRU", "LIS", "Boeing 787-10", "in_air", "warning", "high", "storm", 58, 79, 25],
        ["LF1414", "SIN", "SYD", "Airbus A380", "in_air", "normal", "low", "clear", 33, 28, 3],
        ["LF1502", "DXB", "AMS", "Boeing 777F", "cancelled", "critical", "high", "operational", 0, 88, 25]
    ];

    function byId(id) {
        return document.getElementById(id);
    }

    function collectElements() {
        [
            "flight-map",
            "flights-data",
            "selected-flight-id",

            "mapSearchInput",
            "mapSearchInputMirror",
            "mapStatusSelect",
            "baseLayerSelect",
            "weatherLayerSelect",

            "toggleAircraft",
            "toggleRoutes",
            "toggleAirports",
            "toggleLabels",
            "toggleWeather",
            "toggleRestrictedZones",
            "toggleAlertZones",

            "criticalOnlyBtn",
            "resetMapViewBtn",
            "toggleFullscreenBtn",
            "toggleFullscreenBtnPanel",
            "toggleToolsPanelBtn",
            "closeToolsPanelBtn",
            "mapToolsPanel",
            "clearSelectedFlightBtn",
            "locateMeBtn",
            "focusSelectedBtn",
            "focusSelectedBtnPanel",
            "focusSelectedBtnDrawer",

            "mapRefreshLabel",
            "mapRefreshIcon",
            "mapRefreshState",
            "mapRefreshStateText",

            "visibleFlightsCount",
            "filterCountDelayed",
            "visibleCriticalCount",
            "visibleDisruptionScore",
            "filterCountAll",
            "filterCountInAir",
            "mapStatsDelayedMirror",
            "filterCountCancelled",

            "mapLiveClock",
            "mapStatsClock",
            "mapLocationIndicator",
            "mapLocationText",
            "mapCrisisModeLabel",
            "mapCrisisModeReason",
            "mapEmptyOverlay",

            "weatherHazardList",
            "weatherPreview",

            "selectedFlightEmpty",
            "selectedFlightContent",
            "selectedFlightNumber",
            "selectedFlightRouteText",
            "selectedFlightPriorityBadge",
            "selectedFlightOriginCode",
            "selectedFlightDestinationCode",
            "selectedFlightStatusBadge",
            "selectedFlightRiskLevel",
            "selectedFlightRouteAlertBadge",
            "selectedFlightAirline",
            "selectedFlightAircraft",
            "selectedFlightTrackingLabel",
            "selectedFlightEta",
            "selectedFlightSource",
            "selectedFlightProgress",
            "selectedFlightRemainingDistance",
            "selectedFlightFreshness",
            "selectedFlightRiskScore",
            "selectedFlightTracking",
            "selectedFlightDetailLink",
            "selectedFlightMonitoringLink",
            "selectedFlightMonitoringDetailLink"
        ].forEach(function (id) {
            els[id] = byId(id);
        });
    }

    function parseJsonScript(id, fallback) {
        const node = byId(id);

        if (!node) {
            return fallback;
        }

        try {
            const raw = node.textContent || node.innerText || "";

            if (!raw.trim()) {
                return fallback;
            }

            return JSON.parse(raw);
        } catch (error) {
            console.warn("Unable to parse JSON script:", id, error);
            return fallback;
        }
    }

    function numberOrNull(value) {
        if (value === null || value === undefined || value === "") {
            return null;
        }

        const number = Number(value);

        if (!Number.isFinite(number)) {
            return null;
        }

        return number;
    }

    function clamp(value, min, max) {
        const number = numberOrNull(value);

        if (number === null) {
            return min;
        }

        return Math.max(min, Math.min(max, number));
    }

    function textOr(value, fallback) {
        if (value === null || value === undefined) {
            return fallback || "";
        }

        const normalized = String(value).trim();

        if (!normalized || normalized === "null" || normalized === "undefined") {
            return fallback || "";
        }

        return normalized;
    }

    function cleanSearchValue(value) {
        return textOr(value, "")
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .trim();
    }

    function escapeHtml(value) {
        const div = document.createElement("div");
        div.textContent = value === null || value === undefined ? "" : String(value);
        return div.innerHTML;
    }

    function getCookie(name) {
        const cookies = document.cookie ? document.cookie.split(";") : [];

        for (let i = 0; i < cookies.length; i += 1) {
            const cookie = cookies[i].trim();

            if (cookie.substring(0, name.length + 1) === name + "=") {
                return decodeURIComponent(cookie.substring(name.length + 1));
            }
        }

        return "";
    }

    function updateText(element, value) {
        if (element) {
            element.textContent = value;
        }
    }

    function setHidden(element, hidden) {
        if (element) {
            element.hidden = Boolean(hidden);
        }
    }

    function setLink(element, href) {
        if (!element) {
            return;
        }

        const cleanHref = textOr(href, "#");

        element.setAttribute("href", cleanHref);
        element.classList.toggle("is-disabled", cleanHref === "#");
    }

    function normalizeStatus(status) {
        return textOr(status, "").toLowerCase().replace("-", "_");
    }

    function normalizeLayerValue(value) {
        const cleanValue = textOr(value, "radar").toLowerCase();

        if (cleanValue === "none" || cleanValue === "disabled") {
            return "off";
        }

        if (cleanValue === "rain") {
            return "radar";
        }

        return cleanValue;
    }

    function formatUtcTimeFromUnix(timestamp) {
        const numericTimestamp = numberOrNull(timestamp);

        if (numericTimestamp === null) {
            return "";
        }

        const date = new Date(numericTimestamp * 1000);

        if (Number.isNaN(date.getTime())) {
            return "";
        }

        return date.toISOString().slice(11, 16);
    }

    function formatUtcClock(date) {
        const currentDate = date instanceof Date ? date : new Date();

        return currentDate.toLocaleTimeString("en-GB", {
            timeZone: "UTC",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit"
        }) + " UTC";
    }

    function formatRoute(flight) {
        const origin = textOr(
            flight.origin_code ||
            flight.origin_airport_code ||
            flight.departure_airport_code ||
            flight.departure_iata,
            "N/A"
        );

        const destination = textOr(
            flight.destination_code ||
            flight.destination_airport_code ||
            flight.arrival_airport_code ||
            flight.arrival_iata,
            "N/A"
        );

        return origin + " → " + destination;
    }

    function formatDistance(value) {
        const distance = numberOrNull(value);

        if (distance === null) {
            return "Distance unavailable";
        }

        if (distance < 1) {
            return "Less than 1 km";
        }

        return Math.round(distance).toLocaleString("en-US") + " km";
    }

    function formatRiskScore(value) {
        const score = numberOrNull(value);

        if (score === null) {
            return "—";
        }

        return Math.round(score) + "/100";
    }

    function formatFreshness(flight) {
        const timestamp = numberOrNull(
            flight.updated_at_unix ||
            flight.last_seen_unix ||
            flight.timestamp
        );

        let date = null;

        if (timestamp !== null) {
            date = new Date(timestamp * 1000);
        } else if (flight.updated_at || flight.last_seen_at || flight.last_position_at) {
            date = new Date(flight.updated_at || flight.last_seen_at || flight.last_position_at);
        }

        if (!date || Number.isNaN(date.getTime())) {
            const mode = textOr(flight.tracking_mode || flight.tracking, "").toLowerCase();

            if (mode === "estimated") {
                return "Estimated tracking";
            }

            return "Live freshness unavailable";
        }

        const minutes = Math.max(0, Math.floor((Date.now() - date.getTime()) / 60000));

        if (minutes < 2) {
            return "Just now · fresh";
        }

        if (minutes <= 15) {
            return minutes + " min ago · fresh";
        }

        if (minutes <= 45) {
            return minutes + " min ago · acceptable";
        }

        if (minutes <= 180) {
            return minutes + " min ago · aging";
        }

        return "Aging feed · review source";
    }

    function toDisplayLabel(value) {
        return textOr(value, "")
            .replace(/_/g, " ")
            .replace(/-/g, " ")
            .replace(/\s+/g, " ")
            .trim()
            .replace(/\b\w/g, function (letter) {
                return letter.toUpperCase();
            });
    }

    function hasGoodCoordinates(lat, lng) {
        const cleanLat = numberOrNull(lat);
        const cleanLng = numberOrNull(lng);

        if (cleanLat === null || cleanLng === null) {
            return false;
        }

        if (cleanLat < -90 || cleanLat > 90) {
            return false;
        }

        if (cleanLng < -180 || cleanLng > 180) {
            return false;
        }

        if (Math.abs(cleanLat) < 0.0001 && Math.abs(cleanLng) < 0.0001) {
            return false;
        }

        return true;
    }

    function getAirportByCode(code) {
        const normalizedCode = textOr(code, "").toUpperCase();

        if (!normalizedCode) {
            return null;
        }

        return referenceAirports.find(function (airport) {
            return airport.code === normalizedCode;
        }) || null;
    }

    function buildReferenceFlight(seed, index) {
        const flightNumber = seed[0];
        const originCode = seed[1];
        const destinationCode = seed[2];
        const aircraftType = seed[3];
        const status = seed[4];
        const priority = seed[5];
        const riskLevel = seed[6];
        const routeAlert = seed[7];
        const progress = seed[8];
        const riskScore = seed[9];
        const disruptionScore = seed[10];

        const origin = getAirportByCode(originCode);
        const destination = getAirportByCode(destinationCode);

        return {
            id: "reference-" + flightNumber,
            flight_id: "reference-" + flightNumber,
            flight_number: flightNumber,
            callsign: "LOGOS" + String(index + 101),
            airline_name: "FlightLogos",
            aircraft_type: aircraftType,
            status: status,
            priority: priority,
            risk_level: riskLevel,
            route_alert: routeAlert,
            origin_code: originCode,
            destination_code: destinationCode,
            origin_airport_code: originCode,
            destination_airport_code: destinationCode,
            origin_name: origin ? origin.name : originCode,
            destination_name: destination ? destination.name : destinationCode,
            origin_lat: origin ? origin.lat : null,
            origin_lng: origin ? origin.lng : null,
            destination_lat: destination ? destination.lat : null,
            destination_lng: destination ? destination.lng : null,
            progress: progress,
            risk_score: riskScore,
            disruption_score: disruptionScore,
            tracking_mode: "estimated",
            tracking_label: "Estimated",
            source: "Display layer",
            eta: status === "cancelled" ? "Cancelled" : "Operational ETA available",
            detail_url: "#",
            monitoring_url: "#",
            monitoring_detail_url: "#"
        };
    }

    const referenceFlights = referenceFlightSeeds.map(buildReferenceFlight);

    function normalizeFlight(rawFlight, index) {
        const flight = Object.assign({}, rawFlight || {});

        flight.id = textOr(
            flight.id ||
            flight.flight_id ||
            flight.pk ||
            flight.uuid ||
            flight.flight_number ||
            flight.callsign,
            "flight-" + index
        );

        flight.flight_id = textOr(flight.flight_id || flight.id, flight.id);

        flight.flight_number = textOr(
            flight.flight_number ||
            flight.number ||
            flight.callsign,
            "Flight " + (index + 1)
        );

        flight.callsign = textOr(flight.callsign, flight.flight_number);
        flight.status = normalizeStatus(flight.status || flight.flight_status || "scheduled");

        flight.origin_code = textOr(
            flight.origin_code ||
            flight.origin_airport_code ||
            flight.departure_airport_code ||
            flight.departure_iata,
            ""
        ).toUpperCase();

        flight.destination_code = textOr(
            flight.destination_code ||
            flight.destination_airport_code ||
            flight.arrival_airport_code ||
            flight.arrival_iata,
            ""
        ).toUpperCase();

        flight.origin_airport_code = flight.origin_code;
        flight.destination_airport_code = flight.destination_code;

        const originAirport = getAirportByCode(flight.origin_code);
        const destinationAirport = getAirportByCode(flight.destination_code);

        flight.origin_lat = numberOrNull(
            flight.origin_lat ||
            flight.departure_lat ||
            flight.departure_airport_lat ||
            flight.origin_airport_lat ||
            (originAirport ? originAirport.lat : null)
        );

        flight.origin_lng = numberOrNull(
            flight.origin_lng ||
            flight.origin_lon ||
            flight.departure_lng ||
            flight.departure_lon ||
            flight.departure_airport_lng ||
            flight.departure_airport_lon ||
            flight.origin_airport_lng ||
            flight.origin_airport_lon ||
            (originAirport ? originAirport.lng : null)
        );

        flight.destination_lat = numberOrNull(
            flight.destination_lat ||
            flight.arrival_lat ||
            flight.arrival_airport_lat ||
            flight.destination_airport_lat ||
            (destinationAirport ? destinationAirport.lat : null)
        );

        flight.destination_lng = numberOrNull(
            flight.destination_lng ||
            flight.destination_lon ||
            flight.arrival_lng ||
            flight.arrival_lon ||
            flight.arrival_airport_lng ||
            flight.arrival_airport_lon ||
            flight.destination_airport_lng ||
            flight.destination_airport_lon ||
            (destinationAirport ? destinationAirport.lng : null)
        );

        flight.live_lat = numberOrNull(
            flight.live_lat ||
            flight.latitude ||
            flight.current_lat ||
            flight.position_lat
        );

        flight.live_lng = numberOrNull(
            flight.live_lng ||
            flight.live_lon ||
            flight.longitude ||
            flight.current_lng ||
            flight.current_lon ||
            flight.position_lng ||
            flight.position_lon
        );

        flight.progress = clamp(
            flight.progress ||
            flight.progress_percent ||
            flight.completion ||
            flight.route_progress,
            0,
            100
        );

        flight.heading = numberOrNull(flight.heading || flight.bearing || flight.direction);
        flight.altitude = numberOrNull(flight.altitude || flight.live_altitude);
        flight.speed = numberOrNull(flight.speed || flight.live_speed);

        flight.risk_score = numberOrNull(flight.risk_score || flight.operational_risk_score);
        flight.disruption_score = numberOrNull(flight.disruption_score || flight.impact_score);

        flight.remaining_distance = numberOrNull(
            flight.remaining_distance ||
            flight.remaining_distance_km ||
            flight.distance_remaining_km
        );

        flight.risk_level = textOr(flight.risk_level || flight.risk, "").toLowerCase();
        flight.priority = textOr(flight.priority || flight.operational_priority, "").toLowerCase();
        flight.route_alert = textOr(flight.route_alert || flight.route_exposure || flight.alert_level, "").toLowerCase();
        flight.tracking_mode = textOr(flight.tracking_mode || flight.mode || flight.tracking, "").toLowerCase();
        flight.tracking_label = textOr(flight.tracking_label, flight.tracking_mode || "Tracking");
        flight.source = textOr(flight.source || flight.source_label || flight.data_source, "Internal data");
        flight.eta = textOr(flight.eta || flight.estimated_arrival || flight.arrival_estimate, "");

        flight.airline_name = textOr(
            flight.airline_name ||
            flight.airline ||
            flight.carrier_name,
            "Airline unavailable"
        );

        flight.aircraft_type = textOr(
            flight.aircraft_type ||
            flight.aircraft ||
            flight.aircraft_model,
            "Aircraft unavailable"
        );

        flight.origin_name = textOr(
            flight.origin_name ||
            flight.departure_airport_name ||
            (originAirport ? originAirport.name : ""),
            flight.origin_code || "Origin unavailable"
        );

        flight.destination_name = textOr(
            flight.destination_name ||
            flight.arrival_airport_name ||
            (destinationAirport ? destinationAirport.name : ""),
            flight.destination_code || "Destination unavailable"
        );

        flight.detail_url = textOr(flight.detail_url || flight.url, "#");
        flight.monitoring_url = textOr(flight.monitoring_url, "#");
        flight.monitoring_detail_url = textOr(flight.monitoring_detail_url, "#");

        flight.updated_at = flight.updated_at || flight.last_seen_at || flight.last_position_at || null;
        flight.updated_at_unix = numberOrNull(flight.updated_at_unix || flight.last_seen_unix || flight.timestamp);

        return flight;
    }

    function getCoordinateSpread(flights) {
        const points = [];

        flights.forEach(function (flight) {
            if (hasGoodCoordinates(flight.live_lat, flight.live_lng)) {
                points.push([flight.live_lat, flight.live_lng]);
                return;
            }

            if (hasGoodCoordinates(flight.origin_lat, flight.origin_lng)) {
                points.push([flight.origin_lat, flight.origin_lng]);
            }

            if (hasGoodCoordinates(flight.destination_lat, flight.destination_lng)) {
                points.push([flight.destination_lat, flight.destination_lng]);
            }
        });

        if (points.length < 4) {
            return 0;
        }

        const lats = points.map(function (point) {
            return point[0];
        });

        const lngs = points.map(function (point) {
            return point[1];
        });

        const latSpread = Math.max.apply(null, lats) - Math.min.apply(null, lats);
        const lngSpread = Math.max.apply(null, lngs) - Math.min.apply(null, lngs);

        return Math.max(latSpread, lngSpread);
    }

    function shouldUseDisplayFallback(realFlights) {
        if (!Array.isArray(realFlights) || realFlights.length < 12) {
            return true;
        }

        const validPositionCount = realFlights.filter(function (flight) {
            return getPosition(flight) !== null;
        }).length;

        if (validPositionCount < 12) {
            return true;
        }

        const coordinateSpread = getCoordinateSpread(realFlights);

        if (coordinateSpread > 0 && coordinateSpread < 3.5) {
            return true;
        }

        return false;
    }

    function getSelectedFlightIdFromTemplate() {
        const parsedValue = parseJsonScript("selected-flight-id", "");

        if (parsedValue === null || parsedValue === undefined) {
            return "";
        }

        if (typeof parsedValue === "number") {
            return String(parsedValue);
        }

        if (typeof parsedValue === "string") {
            return textOr(parsedValue, "");
        }

        return "";
    }

    function loadFlights() {
        const rawFlights = parseJsonScript("flights-data", []);

        const normalizedRealFlights = Array.isArray(rawFlights)
            ? rawFlights.map(normalizeFlight)
            : [];

        const normalizedReferenceFlights = referenceFlights.map(normalizeFlight);

        state.realFlights = normalizedRealFlights;
        state.estimatedLayerEnabled = shouldUseDisplayFallback(normalizedRealFlights);

        if (state.estimatedLayerEnabled) {
            state.flights = normalizedReferenceFlights.concat(normalizedRealFlights.slice(0, 8));
        } else {
            state.flights = normalizedRealFlights;
        }

        const selectedFlightId = getSelectedFlightIdFromTemplate();

        if (selectedFlightId) {
            state.selectedFlightId = selectedFlightId;
        }
    }

    function syncThemeClass() {
        const mapRoot = els["flight-map"];

        if (!mapRoot) {
            return;
        }

        const html = document.documentElement;
        const body = document.body;

        const themeValue = [
            html.getAttribute("data-theme"),
            body.getAttribute("data-theme"),
            html.className,
            body.className
        ].join(" ").toLowerCase();

        const darkMode = themeValue.includes("dark") ||
            body.classList.contains("theme-dark") ||
            body.classList.contains("dark") ||
            html.classList.contains("dark");

        mapRoot.classList.toggle("logosflight-map-dark-ui", darkMode);
    }

    function initializeLeafletLayers() {
        if (typeof L === "undefined") {
            return false;
        }

        state.layers.aircraft = L.layerGroup();
        state.layers.routes = L.layerGroup();
        state.layers.labels = L.layerGroup();
        state.layers.airports = L.layerGroup();
        state.layers.restrictedZones = L.layerGroup();
        state.layers.weather = L.layerGroup();

        return true;
    }

    function initializeMap() {
        const mapContainer = els["flight-map"];

        if (!mapContainer || typeof L === "undefined") {
            console.warn("Leaflet map container is missing or Leaflet is not loaded.");
            return;
        }

        if (!initializeLeafletLayers()) {
            console.warn("Unable to initialize Leaflet layers.");
            return;
        }

        state.map = L.map(mapContainer, {
            center: DEFAULT_CENTER,
            zoom: DEFAULT_ZOOM,
            minZoom: MIN_ZOOM,
            maxZoom: MAX_ZOOM,
            zoomControl: false,
            preferCanvas: true,
            zoomSnap: 0.5,
            worldCopyJump: true
        });

        state.map.createPane("rainviewerRadarPane");
        state.map.getPane("rainviewerRadarPane").style.zIndex = 330;
        state.map.getPane("rainviewerRadarPane").style.pointerEvents = "none";

        L.control.zoom({ position: "topright" }).addTo(state.map);

        state.layers.routes.addTo(state.map);
        state.layers.airports.addTo(state.map);
        state.layers.restrictedZones.addTo(state.map);
        state.layers.weather.addTo(state.map);
        state.layers.aircraft.addTo(state.map);
        state.layers.labels.addTo(state.map);

        setBaseLayer(state.baseLayerKey);

        state.map.on("moveend zoomend", function () {
            scheduleRender();
        });
    }

    function setBaseLayer(layerKey) {
        if (!state.map) {
            return;
        }

        const cleanKey = baseLayers[layerKey] ? layerKey : "dark";
        const layerConfig = baseLayers[cleanKey];

        if (state.baseLayer) {
            state.map.removeLayer(state.baseLayer);
        }

        state.baseLayer = L.tileLayer(layerConfig.url, layerConfig.options);
        state.baseLayer.addTo(state.map);
        state.baseLayerKey = cleanKey;

        if (els.baseLayerSelect && els.baseLayerSelect.value !== cleanKey) {
            els.baseLayerSelect.value = cleanKey;
        }
    }

    function getStatusColor(status) {
        const normalized = normalizeStatus(status);

        if (
            normalized === "in_air" ||
            normalized === "active" ||
            normalized === "departed" ||
            normalized === "enroute" ||
            normalized === "en_route"
        ) {
            return "#38bdf8";
        }

        if (normalized === "boarding" || normalized === "scheduled") {
            return "#a3e635";
        }

        if (normalized === "landed") {
            return "#22c55e";
        }

        if (normalized === "delayed") {
            return "#f59e0b";
        }

        if (normalized === "cancelled") {
            return "#ef4444";
        }

        return "#94a3b8";
    }

    function getStatusWeight(status) {
        const normalized = normalizeStatus(status);

        if (normalized === "cancelled") {
            return 4;
        }

        if (normalized === "delayed") {
            return 3;
        }

        if (
            normalized === "in_air" ||
            normalized === "active" ||
            normalized === "departed"
        ) {
            return 2.6;
        }

        return 2;
    }

    function isInAirStatus(status) {
        const normalized = normalizeStatus(status);

        return normalized === "in_air" ||
            normalized === "active" ||
            normalized === "departed" ||
            normalized === "enroute" ||
            normalized === "en_route";
    }

    function isCriticalFlight(flight) {
        if (!flight) {
            return false;
        }

        const status = normalizeStatus(flight.status);
        const priority = textOr(flight.priority, "").toLowerCase();
        const riskLevel = textOr(flight.risk_level, "").toLowerCase();
        const routeAlert = textOr(flight.route_alert, "").toLowerCase();
        const riskScore = numberOrNull(flight.risk_score);
        const disruptionScore = numberOrNull(flight.disruption_score);

        return status === "cancelled" ||
            priority === "critical" ||
            riskLevel === "high" ||
            routeAlert === "storm" ||
            routeAlert === "critical" ||
            (riskScore !== null && riskScore >= 82) ||
            (disruptionScore !== null && disruptionScore >= 25);
    }

    function getFlightById(flightId) {
        const id = textOr(flightId, "");

        if (!id) {
            return null;
        }

        return state.flights.find(function (flight) {
            return String(flight.id) === id ||
                String(flight.flight_id) === id ||
                String(flight.flight_number) === id;
        }) || null;
    }

    function flightMatchesSearch(flight, query) {
        const cleanQuery = cleanSearchValue(query);

        if (!cleanQuery) {
            return true;
        }

        const searchable = [
            flight.flight_number,
            flight.callsign,
            flight.airline_name,
            flight.aircraft_type,
            flight.origin_code,
            flight.destination_code,
            flight.origin_name,
            flight.destination_name,
            flight.status
        ].map(cleanSearchValue).join(" ");

        return searchable.includes(cleanQuery);
    }

    function getFilteredFlights() {
        const statusFilter = normalizeStatus(state.statusFilter);

        return state.flights.filter(function (flight) {
            if (state.toggles.criticalOnly && !isCriticalFlight(flight)) {
                return false;
            }

            if (!flightMatchesSearch(flight, state.searchQuery)) {
                return false;
            }

            if (statusFilter !== "all" && normalizeStatus(flight.status) !== statusFilter) {
                return false;
            }

            return true;
        });
    }

    function getVisibleFlights() {
        return getFilteredFlights().filter(function (flight) {
            return getPosition(flight) !== null;
        });
    }

    function getPosition(flight) {
        if (!flight) {
            return null;
        }

        if (hasGoodCoordinates(flight.live_lat, flight.live_lng)) {
            return {
                lat: numberOrNull(flight.live_lat),
                lng: numberOrNull(flight.live_lng),
                source: "live"
            };
        }

        const originLat = numberOrNull(flight.origin_lat);
        const originLng = numberOrNull(flight.origin_lng);
        const destinationLat = numberOrNull(flight.destination_lat);
        const destinationLng = numberOrNull(flight.destination_lng);

        if (
            !hasGoodCoordinates(originLat, originLng) ||
            !hasGoodCoordinates(destinationLat, destinationLng)
        ) {
            return null;
        }

        const progress = clamp(flight.progress, 0, 100) / 100;

        return {
            lat: originLat + (destinationLat - originLat) * progress,
            lng: originLng + (destinationLng - originLng) * progress,
            source: "interpolated"
        };
    }

    function getHeadingBetween(originLat, originLng, destinationLat, destinationLng) {
        const startLat = numberOrNull(originLat);
        const startLng = numberOrNull(originLng);
        const endLat = numberOrNull(destinationLat);
        const endLng = numberOrNull(destinationLng);

        if (
            startLat === null ||
            startLng === null ||
            endLat === null ||
            endLng === null
        ) {
            return 45;
        }

        const startLatRad = startLat * Math.PI / 180;
        const endLatRad = endLat * Math.PI / 180;
        const deltaLngRad = (endLng - startLng) * Math.PI / 180;

        const y = Math.sin(deltaLngRad) * Math.cos(endLatRad);
        const x = Math.cos(startLatRad) * Math.sin(endLatRad) -
            Math.sin(startLatRad) * Math.cos(endLatRad) * Math.cos(deltaLngRad);

        const bearing = Math.atan2(y, x) * 180 / Math.PI;

        return (bearing + 360) % 360;
    }

    function createPlaneIcon(flight, heading) {
        const status = normalizeStatus(flight.status);
        const color = getStatusColor(status);
        const rotation = numberOrNull(heading) !== null ? heading : 45;
        const critical = isCriticalFlight(flight);

        const html = [
            '<div class="map-plane-icon',
            critical ? ' map-plane-icon-critical' : '',
            '" style="--plane-color:', escapeHtml(color), '; transform: rotate(', rotation, 'deg);">',
            '<span class="map-plane-symbol">✈</span>',
            '</div>'
        ].join("");

        return L.divIcon({
            className: "logosflight-plane-marker",
            html: html,
            iconSize: [34, 34],
            iconAnchor: [17, 17],
            popupAnchor: [0, -18]
        });
    }

    function createInvisibleAirportMarkerIcon() {
        return L.divIcon({
            className: "logosflight-airport-invisible-marker",
            html: "<span></span>",
            iconSize: [1, 1],
            iconAnchor: [0, 0]
        });
    }

    function getImportantAirportCodes() {
        const codes = new Set();

        referenceAirports.forEach(function (airport) {
            if (airport.hub) {
                codes.add(airport.code);
            }
        });

        state.visibleFlights.forEach(function (flight) {
            if (isCriticalFlight(flight)) {
                if (flight.origin_code) {
                    codes.add(flight.origin_code);
                }

                if (flight.destination_code) {
                    codes.add(flight.destination_code);
                }
            }
        });

        if (state.selectedFlightId) {
            const selectedFlight = getFlightById(state.selectedFlightId);

            if (selectedFlight) {
                if (selectedFlight.origin_code) {
                    codes.add(selectedFlight.origin_code);
                }

                if (selectedFlight.destination_code) {
                    codes.add(selectedFlight.destination_code);
                }
            }
        }

        return Array.from(codes).slice(0, AIRPORT_LABEL_LIMIT);
    }

    function createAirportLabelIcon(airport) {
        const html = [
            '<div class="map-airport-label">',
            '<span class="map-airport-code">', escapeHtml(airport.code), '</span>',
            '</div>'
        ].join("");

        return L.divIcon({
            className: "logosflight-airport-label-marker",
            html: html,
            iconSize: [46, 22],
            iconAnchor: [23, 11]
        });
    }

    function getFlightLabelOffset(flight, index) {
        const selected = state.selectedFlightId &&
            (
                String(flight.id) === String(state.selectedFlightId) ||
                String(flight.flight_id) === String(state.selectedFlightId)
            );

        if (selected) {
            return [24, -24];
        }

        const offsets = [
            [18, -18],
            [-18, -18],
            [18, 18],
            [-18, 18],
            [26, 0],
            [-26, 0]
        ];

        return offsets[index % offsets.length];
    }

    function createFlightLabelIcon(flight, index) {
        const status = normalizeStatus(flight.status);
        const color = getStatusColor(status);
        const offset = getFlightLabelOffset(flight, index);
        const critical = isCriticalFlight(flight);
        const selected = state.selectedFlightId &&
            (
                String(flight.id) === String(state.selectedFlightId) ||
                String(flight.flight_id) === String(state.selectedFlightId)
            );

        const html = [
            '<div class="map-flight-label',
            critical ? ' map-flight-label-critical' : '',
            selected ? ' map-flight-label-selected' : '',
            '" style="--label-color:', escapeHtml(color), ';">',
            '<span class="map-flight-label-number">', escapeHtml(flight.flight_number), '</span>',
            '<span class="map-flight-label-route">', escapeHtml(formatRoute(flight)), '</span>',
            '</div>'
        ].join("");

        return L.divIcon({
            className: "logosflight-flight-label-marker",
            html: html,
            iconSize: [118, 42],
            iconAnchor: [0 - offset[0], 21 - offset[1]]
        });
    }

    function clearLayerGroup(layerGroup) {
        if (!layerGroup) {
            return;
        }

        layerGroup.clearLayers();
    }

    function clearOperationalLayers() {
        clearLayerGroup(state.layers.aircraft);
        clearLayerGroup(state.layers.routes);
        clearLayerGroup(state.layers.labels);
        clearLayerGroup(state.layers.airports);
        clearLayerGroup(state.layers.restrictedZones);
        clearLayerGroup(state.layers.weather);

        state.markers.aircraft = [];
        state.markers.routes = [];
        state.markers.labels = [];
        state.markers.airports = [];
        state.markers.restrictedZones = [];
        state.markers.weather = [];
    }

    function drawRoute(flight, options) {
        if (!state.map || !flight) {
            return null;
        }

        const originLat = numberOrNull(flight.origin_lat);
        const originLng = numberOrNull(flight.origin_lng);
        const destinationLat = numberOrNull(flight.destination_lat);
        const destinationLng = numberOrNull(flight.destination_lng);

        if (
            !hasGoodCoordinates(originLat, originLng) ||
            !hasGoodCoordinates(destinationLat, destinationLng)
        ) {
            return null;
        }

        const status = normalizeStatus(flight.status);
        const selected = options && options.selected;
        const critical = isCriticalFlight(flight);

        const route = L.polyline(
            [
                [originLat, originLng],
                [destinationLat, destinationLng]
            ],
            {
                color: getStatusColor(status),
                weight: selected ? 3.8 : critical ? 2.8 : getStatusWeight(status),
                opacity: selected ? 0.9 : critical ? 0.72 : 0.35,
                dashArray: selected ? null : critical ? "8 7" : "4 8",
                lineCap: "round",
                lineJoin: "round",
                interactive: false
            }
        );

        route.addTo(state.layers.routes);
        state.markers.routes.push(route);

        return route;
    }

    function renderAirports() {
        if (!state.toggles.airports || !state.layers.airports) {
            return;
        }

        const importantAirportCodes = getImportantAirportCodes();
        const renderedCodes = new Set();

        referenceAirports.forEach(function (airport) {
            const invisibleMarker = L.marker([airport.lat, airport.lng], {
                icon: createInvisibleAirportMarkerIcon(),
                keyboard: false,
                opacity: 0
            });

            invisibleMarker.bindTooltip(
                [
                    '<div class="map-airport-tooltip">',
                    '<strong>', escapeHtml(airport.code), '</strong>',
                    '<span>', escapeHtml(airport.name), '</span>',
                    '<small>', escapeHtml(airport.city), ', ', escapeHtml(airport.country), '</small>',
                    '</div>'
                ].join(""),
                {
                    direction: "top",
                    opacity: 0.94,
                    sticky: true,
                    className: "logosflight-airport-tooltip"
                }
            );

            invisibleMarker.addTo(state.layers.airports);
            state.markers.airports.push(invisibleMarker);

            if (
                importantAirportCodes.includes(airport.code) &&
                !renderedCodes.has(airport.code)
            ) {
                const label = L.marker([airport.lat, airport.lng], {
                    icon: createAirportLabelIcon(airport),
                    keyboard: false,
                    interactive: false
                });

                label.addTo(state.layers.labels);
                state.markers.labels.push(label);
                renderedCodes.add(airport.code);
            }
        });
    }

    function renderRestrictedZones() {
        if (!state.layers.restrictedZones) {
            return;
        }

        if (!state.toggles.restrictedZones && !state.toggles.alertZones) {
            return;
        }

        const zones = [
            {
                name: "North Atlantic coordination sector",
                center: [55.5, -24.0],
                radius: 780000,
                type: "monitored",
                enabled: state.toggles.restrictedZones
            },
            {
                name: "Central Europe disruption watch",
                center: [50.7, 14.0],
                radius: 420000,
                type: "attention",
                enabled: state.toggles.alertZones
            },
            {
                name: "Eastern Mediterranean weather exposure",
                center: [36.5, 29.5],
                radius: 360000,
                type: "weather",
                enabled: state.toggles.alertZones
            }
        ];

        zones.forEach(function (zone) {
            if (!zone.enabled) {
                return;
            }

            const color = zone.type === "attention"
                ? "#f59e0b"
                : zone.type === "weather"
                    ? "#38bdf8"
                    : "#94a3b8";

            const circle = L.circle(zone.center, {
                radius: zone.radius,
                color: color,
                weight: 1.2,
                opacity: 0.5,
                fillColor: color,
                fillOpacity: 0.055,
                interactive: false
            });

            circle.addTo(state.layers.restrictedZones);
            state.markers.restrictedZones.push(circle);
        });
    }

    function shouldDisplayWeatherLayer() {
        return state.toggles.weather &&
            normalizeLayerValue(state.weatherLayerKey) !== "off";
    }

    function removeRadarLayer() {
        if (state.radarLayer && state.map) {
            state.map.removeLayer(state.radarLayer);
        }

        state.radarLayer = null;
        state.radarTileUrl = null;
        state.radarTimestamp = null;
        state.radarActive = false;
    }

    function applyRadarLayer(radar) {
        if (!state.map) {
            return;
        }

        removeRadarLayer();

        if (!radar || !radar.available || !radar.tile_url) {
            return;
        }

        state.radarTileUrl = radar.tile_url;
        state.radarTimestamp = radar.timestamp || radar.time || null;

        if (!shouldDisplayWeatherLayer()) {
            return;
        }

        state.radarLayer = L.tileLayer(radar.tile_url, {
            pane: "rainviewerRadarPane",
            opacity: 0.56,
            zIndex: 330,
            maxZoom: 12,
            tileSize: 256,
            crossOrigin: true,
            attribution: "Weather radar © RainViewer"
        });

        state.radarLayer.addTo(state.map);
        state.radarActive = true;
    }

    function getWeatherAirports() {
        const airportMap = new Map();

        referenceAirports.forEach(function (airport) {
            airportMap.set(airport.code, {
                code: airport.code,
                name: airport.name,
                lat: airport.lat,
                lng: airport.lng,
                hub: Boolean(airport.hub)
            });
        });

        state.visibleFlights.forEach(function (flight) {
            if (
                flight.origin_code &&
                hasGoodCoordinates(flight.origin_lat, flight.origin_lng)
            ) {
                airportMap.set(flight.origin_code, {
                    code: flight.origin_code,
                    name: flight.origin_name,
                    lat: flight.origin_lat,
                    lng: flight.origin_lng,
                    hub: false
                });
            }

            if (
                flight.destination_code &&
                hasGoodCoordinates(flight.destination_lat, flight.destination_lng)
            ) {
                airportMap.set(flight.destination_code, {
                    code: flight.destination_code,
                    name: flight.destination_name,
                    lat: flight.destination_lat,
                    lng: flight.destination_lng,
                    hub: false
                });
            }
        });

        return Array.from(airportMap.values()).slice(0, 36);
    }

    function buildOperationalSummary() {
        const visibleFlights = state.visibleFlights || [];

        const delayed = visibleFlights.filter(function (flight) {
            return normalizeStatus(flight.status) === "delayed";
        }).length;

        const cancelled = visibleFlights.filter(function (flight) {
            return normalizeStatus(flight.status) === "cancelled";
        }).length;

        const inAir = visibleFlights.filter(function (flight) {
            return isInAirStatus(flight.status);
        }).length;

        const critical = visibleFlights.filter(isCriticalFlight).length;

        const disruptionScore = visibleFlights.reduce(function (total, flight) {
            const score = numberOrNull(flight.disruption_score);
            return total + (score || 0);
        }, 0);

        return {
            total_visible: visibleFlights.length,
            in_air: inAir,
            delayed: delayed,
            cancelled: cancelled,
            critical: critical,
            disruption_score: Math.round(disruptionScore),
            estimated_layer_enabled: state.estimatedLayerEnabled,
            selected_flight_id: state.selectedFlightId || null,
            status_filter: state.statusFilter,
            search_query: state.searchQuery
        };
    }

    function scheduleBackendWeatherRefresh() {
        if (state.weatherTimer) {
            window.clearInterval(state.weatherTimer);
        }

        refreshBackendWeather();

        state.weatherTimer = window.setInterval(function () {
            refreshBackendWeather();
        }, WEATHER_REFRESH_INTERVAL_MS);
    }

    function refreshBackendWeather() {
        if (!shouldDisplayWeatherLayer()) {
            removeRadarLayer();
            updateWeatherPanel(null);
            return Promise.resolve(null);
        }

        const payload = {
            airports: getWeatherAirports(),
            operational_summary: buildOperationalSummary()
        };

        return fetch(WEATHER_ENDPOINT, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"),
                "X-Requested-With": "XMLHttpRequest"
            },
            body: JSON.stringify(payload)
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("Weather endpoint returned " + response.status);
                }

                return response.json();
            })
            .then(function (data) {
                state.lastWeatherPayload = data || {};
                state.lastWeatherRefreshAt = new Date();

                if (data && data.radar) {
                    applyRadarLayer(data.radar);
                } else {
                    removeRadarLayer();
                }

                renderWeatherHazards(data);
                updateWeatherPanel(data);

                return data;
            })
            .catch(function (error) {
                console.warn("Weather refresh failed:", error);
                removeRadarLayer();
                renderWeatherHazards(null);
                updateWeatherPanel(null);

                return null;
            });
    }

    function renderRealWeatherMarkers(payload) {
        if (!shouldDisplayWeatherLayer() || !state.layers.weather) {
            return;
        }

        const hazards = payload && Array.isArray(payload.hazards)
            ? payload.hazards
            : [];

        hazards.forEach(function (hazard) {
            const lat = numberOrNull(hazard.lat || hazard.latitude);
            const lng = numberOrNull(hazard.lng || hazard.lon || hazard.longitude);

            if (!hasGoodCoordinates(lat, lng)) {
                return;
            }

            const severity = textOr(hazard.severity || hazard.level, "normal").toLowerCase();
            const type = textOr(hazard.type || hazard.category, "weather").toLowerCase();

            const color = severity === "high" || severity === "critical"
                ? "#ef4444"
                : severity === "medium" || severity === "warning"
                    ? "#f59e0b"
                    : "#38bdf8";

            const marker = L.circleMarker([lat, lng], {
                radius: severity === "high" || severity === "critical" ? 9 : 6,
                color: color,
                weight: 1.5,
                opacity: 0.88,
                fillColor: color,
                fillOpacity: 0.28
            });

            marker.bindTooltip(
                [
                    '<div class="map-weather-tooltip">',
                    '<strong>', escapeHtml(textOr(hazard.title || hazard.name, "Weather exposure")), '</strong>',
                    '<span>', escapeHtml(type), '</span>',
                    '</div>'
                ].join(""),
                {
                    direction: "top",
                    sticky: true,
                    opacity: 0.94,
                    className: "logosflight-weather-tooltip"
                }
            );

            marker.addTo(state.layers.weather);
            state.markers.weather.push(marker);
        });
    }

    function renderWeatherHazards(payload) {
        clearLayerGroup(state.layers.weather);
        state.markers.weather = [];

        if (!shouldDisplayWeatherLayer() || !state.layers.weather) {
            return;
        }

        renderRealWeatherMarkers(payload);

        const summary = payload && payload.summary ? payload.summary : {};
        const pressureActive = Boolean(
            summary.operational_pressure_active ||
            summary.pressure_active ||
            (
                numberOrNull(summary.disruption_score) !== null &&
                numberOrNull(summary.disruption_score) > 0
            )
        );

        if (!pressureActive) {
            return;
        }

        const watchZones = [
            {
                center: [50.0, 8.5],
                radius: 220000,
                label: "Operational pressure active"
            },
            {
                center: [41.0, 28.5],
                radius: 260000,
                label: "Weather watch sector"
            }
        ];

        watchZones.forEach(function (zone) {
            const circle = L.circle(zone.center, {
                radius: zone.radius,
                color: "#f59e0b",
                weight: 1.4,
                opacity: 0.42,
                fillColor: "#f59e0b",
                fillOpacity: 0.07,
                interactive: false
            });

            circle.addTo(state.layers.weather);
            state.markers.weather.push(circle);
        });
    }

    function buildMiniRadarTileStyle(radar) {
        if (!radar || !radar.available || !radar.tile_url) {
            return "";
        }

        const sampleZ = numberOrNull(radar.preview_z) || 4;
        const sampleX = numberOrNull(radar.preview_x) || 8;
        const sampleY = numberOrNull(radar.preview_y) || 5;

        const tileUrl = radar.tile_url
            .replace("{z}", sampleZ)
            .replace("{x}", sampleX)
            .replace("{y}", sampleY)
            .replace("{s}", "tilecache");

        return [
            "background-color:#06111f;",
            "background-image:",
            "linear-gradient(135deg, rgba(15,23,42,0.92), rgba(2,6,23,0.78)),",
            "radial-gradient(circle at 30% 25%, rgba(56,189,248,0.18), transparent 38%),",
            "url('", escapeHtml(tileUrl), "');",
            "background-size:cover;",
            "background-position:center;",
            "background-blend-mode:normal,screen,normal;"
        ].join("");
    }

    function getWeatherText(payload) {
        const summary = payload && payload.summary ? payload.summary : {};
        const radar = payload && payload.radar ? payload.radar : {};
        const hazards = payload && Array.isArray(payload.hazards) ? payload.hazards : [];

        const pressureActive = Boolean(
            summary.operational_pressure_active ||
            summary.pressure_active ||
            hazards.some(function (hazard) {
                return textOr(hazard.type || hazard.category, "").toLowerCase().includes("pressure");
            })
        );

        const stormRisk = Boolean(
            summary.storm_risk ||
            hazards.some(function (hazard) {
                const type = textOr(hazard.type || hazard.category || hazard.title, "").toLowerCase();
                const severity = textOr(hazard.severity || hazard.level, "").toLowerCase();

                return type.includes("storm") ||
                    type.includes("convective") ||
                    severity === "critical";
            })
        );

        const windExposure = Boolean(
            summary.wind_exposure ||
            hazards.some(function (hazard) {
                return textOr(hazard.type || hazard.category || hazard.title, "").toLowerCase().includes("wind");
            })
        );

        const visibilityIssue = Boolean(
            summary.visibility_issue ||
            hazards.some(function (hazard) {
                return textOr(hazard.type || hazard.category || hazard.title, "").toLowerCase().includes("visibility");
            })
        );

        const radarText = radar && radar.available && radar.timestamp
            ? "Live radar scan · " + formatUtcTimeFromUnix(radar.timestamp) + " UTC"
            : radar && radar.available
                ? "Live radar scan · UTC feed active"
                : "No active precipitation";

        return [
            radarText,
            pressureActive ? "Operational pressure active" : "No disruption pressure",
            stormRisk ? "Storm risk monitored" : "No storm risk",
            windExposure ? "Wind exposure monitored" : "No major wind exposure",
            visibilityIssue ? "Visibility watch active" : "Visibility normal",
            "Restricted zones monitored"
        ];
    }

    function updateWeatherPanel(payload) {
        const weatherTexts = getWeatherText(payload);

        if (els.weatherHazardList) {
            els.weatherHazardList.innerHTML = weatherTexts.map(function (item) {
                return [
                    '<li class="weather-hazard-item">',
                    '<span class="weather-hazard-dot"></span>',
                    '<span>', escapeHtml(item), '</span>',
                    '</li>'
                ].join("");
            }).join("");
        }

        if (!els.weatherPreview) {
            return;
        }

        const radar = payload && payload.radar ? payload.radar : null;
        const previewStyle = buildMiniRadarTileStyle(radar);
        const radarActive = Boolean(
            shouldDisplayWeatherLayer() &&
            radar &&
            radar.available &&
            radar.tile_url &&
            previewStyle
        );

        if (radarActive) {
            els.weatherPreview.innerHTML = [
                '<div class="weather-radar-image-only weather-radar-image-live" style="',
                previewStyle,
                '"></div>'
            ].join("");
            return;
        }

        els.weatherPreview.innerHTML = [
            '<div class="weather-radar-image-only weather-radar-visual-standby">',
            '<span class="weather-radar-visual-cell weather-radar-visual-cell-a"></span>',
            '<span class="weather-radar-visual-cell weather-radar-visual-cell-b"></span>',
            '<span class="weather-radar-visual-cell weather-radar-visual-cell-c"></span>',
            '<span class="weather-radar-zone weather-radar-zone-a"></span>',
            '<span class="weather-radar-zone weather-radar-zone-b"></span>',
            '<span class="weather-radar-line weather-radar-line-a"></span>',
            '<span class="weather-radar-line weather-radar-line-b"></span>',
            '<span class="weather-radar-line weather-radar-line-c"></span>',
            '</div>'
        ].join("");
    }

    function buildPopup(flight) {
        const status = normalizeStatus(flight.status).replace(/_/g, " ");
        const riskScore = formatRiskScore(flight.risk_score);
        const route = formatRoute(flight);

        return [
            '<div class="map-flight-popup">',
            '<div class="map-flight-popup-header">',
            '<strong>', escapeHtml(flight.flight_number), '</strong>',
            '<span>', escapeHtml(status), '</span>',
            '</div>',
            '<div class="map-flight-popup-route">', escapeHtml(route), '</div>',
            '<div class="map-flight-popup-meta">',
            '<span>', escapeHtml(flight.airline_name), '</span>',
            '<span>Risk ', escapeHtml(riskScore), '</span>',
            '</div>',
            '<button type="button" class="map-flight-popup-action" data-flight-select="', escapeHtml(flight.id), '">',
            'Open flight',
            '</button>',
            '</div>'
        ].join("");
    }

    function renderFlights() {
        if (!state.map) {
            return;
        }

        state.filteredFlights = getFilteredFlights();
        state.visibleFlights = getVisibleFlights();

        clearOperationalLayers();

        renderRestrictedZones();
        renderAirports();

        if (shouldDisplayWeatherLayer() && state.lastWeatherPayload) {
            renderWeatherHazards(state.lastWeatherPayload);
        }

        const selectedFlight = state.selectedFlightId
            ? getFlightById(state.selectedFlightId)
            : null;

        const sortedFlights = state.visibleFlights.slice().sort(function (a, b) {
            if (String(a.id) === String(state.selectedFlightId)) {
                return -1;
            }

            if (String(b.id) === String(state.selectedFlightId)) {
                return 1;
            }

            const aCritical = isCriticalFlight(a) ? 1 : 0;
            const bCritical = isCriticalFlight(b) ? 1 : 0;

            if (aCritical !== bCritical) {
                return bCritical - aCritical;
            }

            const aScore = numberOrNull(a.risk_score) || 0;
            const bScore = numberOrNull(b.risk_score) || 0;

            return bScore - aScore;
        });

        const criticalRoutes = sortedFlights.filter(isCriticalFlight).slice(0, CRITICAL_ROUTE_DISPLAY_LIMIT);
        const standardRoutes = sortedFlights.filter(function (flight) {
            return !isCriticalFlight(flight);
        }).slice(0, ROUTE_DISPLAY_LIMIT);

        const routesToRender = new Set();

        criticalRoutes.concat(standardRoutes).forEach(function (flight) {
            routesToRender.add(String(flight.id));
        });

        if (selectedFlight) {
            routesToRender.add(String(selectedFlight.id));
        }

        if (state.toggles.routes) {
            sortedFlights.forEach(function (flight) {
                if (!routesToRender.has(String(flight.id))) {
                    return;
                }

                drawRoute(flight, {
                    selected: selectedFlight && String(flight.id) === String(selectedFlight.id)
                });
            });
        }

        if (state.toggles.aircraft) {
            sortedFlights.forEach(function (flight) {
                const position = getPosition(flight);

                if (!position) {
                    return;
                }

                const heading = numberOrNull(flight.heading) !== null
                    ? flight.heading
                    : getHeadingBetween(
                        flight.origin_lat,
                        flight.origin_lng,
                        flight.destination_lat,
                        flight.destination_lng
                    );

                const marker = L.marker([position.lat, position.lng], {
                    icon: createPlaneIcon(flight, heading),
                    title: flight.flight_number,
                    keyboard: true,
                    riseOnHover: true
                });

                marker.bindPopup(buildPopup(flight), {
                    className: "logosflight-flight-popup",
                    closeButton: true,
                    minWidth: 230
                });

                marker.on("click", function () {
                    selectFlight(flight.id, {
                        focus: false,
                        openPopup: false
                    });
                });

                marker.addTo(state.layers.aircraft);
                state.markers.aircraft.push(marker);
            });
        }

        if (state.toggles.labels) {
            const selectedLabelFlights = sortedFlights.filter(function (flight) {
                return String(flight.id) === String(state.selectedFlightId);
            });

            const criticalLabelFlights = sortedFlights.filter(function (flight) {
                return isCriticalFlight(flight) &&
                    String(flight.id) !== String(state.selectedFlightId);
            });

            const labelFlights = selectedLabelFlights
                .concat(criticalLabelFlights)
                .slice(0, LABEL_DISPLAY_LIMIT);

            labelFlights.forEach(function (flight, index) {
                const position = getPosition(flight);

                if (!position) {
                    return;
                }

                const label = L.marker([position.lat, position.lng], {
                    icon: createFlightLabelIcon(flight, index),
                    keyboard: false,
                    interactive: false,
                    zIndexOffset: String(flight.id) === String(state.selectedFlightId) ? 1000 : 500
                });

                label.addTo(state.layers.labels);
                state.markers.labels.push(label);
            });
        }

        if (state.selectedFlightId && !getFlightById(state.selectedFlightId)) {
            state.selectedFlightId = null;
        }

        updateSelectedPanel();
        updateCounters();
        updateCrisisBanner();
        toggleEmptyState();

        window.setTimeout(function () {
            if (state.map) {
                state.map.invalidateSize(false);
            }
        }, 40);
    }

    function setReferenceView() {
        if (!state.map) {
            return;
        }

        const flightsForBounds = state.visibleFlights.length
            ? state.visibleFlights
            : state.flights;

        const boundsPoints = [];

        flightsForBounds.forEach(function (flight) {
            const position = getPosition(flight);

            if (position) {
                boundsPoints.push([position.lat, position.lng]);
            }

            if (hasGoodCoordinates(flight.origin_lat, flight.origin_lng)) {
                boundsPoints.push([flight.origin_lat, flight.origin_lng]);
            }

            if (hasGoodCoordinates(flight.destination_lat, flight.destination_lng)) {
                boundsPoints.push([flight.destination_lat, flight.destination_lng]);
            }
        });

        if (boundsPoints.length >= 2) {
            state.map.fitBounds(boundsPoints, {
                padding: [42, 42],
                maxZoom: 6.5,
                animate: true
            });
            return;
        }

        state.map.setView(DEFAULT_CENTER, DEFAULT_ZOOM, {
            animate: true
        });
    }

    function focusSelectedFlight() {
        if (!state.map || !state.selectedFlightId) {
            return;
        }

        const selectedFlight = getFlightById(state.selectedFlightId);
        const position = selectedFlight ? getPosition(selectedFlight) : null;

        if (!selectedFlight || !position) {
            return;
        }

        state.map.setView([position.lat, position.lng], Math.max(state.map.getZoom(), 6.5), {
            animate: true,
            duration: 0.45
        });
    }

    function selectFlight(flightId, options) {
        const flight = getFlightById(flightId);

        if (!flight) {
            return;
        }

        state.selectedFlightId = String(flight.id);

        renderFlights();

        if (options && options.focus) {
            focusSelectedFlight();
        }
    }

    function clearSelectedFlight() {
        state.selectedFlightId = null;
        renderFlights();
    }

    function getPriorityMeta(flight) {
        const priority = textOr(flight.priority || flight.operational_priority, "normal").toLowerCase();

        if (priority === "critical" || priority === "immediate") {
            return {
                label: "Critical",
                className: "urgency-critical"
            };
        }

        if (priority === "high" || priority === "warning") {
            return {
                label: "High",
                className: "urgency-warning"
            };
        }

        if (priority === "attention" || priority === "active") {
            return {
                label: "Attention",
                className: "urgency-attention"
            };
        }

        return {
            label: "Normal",
            className: "urgency-normal"
        };
    }

    function getRiskClass(flight) {
        const riskLevel = textOr(flight.risk_level, "").toLowerCase();
        const riskScore = numberOrNull(flight.risk_score);

        if (riskLevel === "high" || riskScore >= 82) {
            return {
                label: "High risk",
                className: "risk-high"
            };
        }

        if (riskLevel === "medium" || riskScore >= 45) {
            return {
                label: "Medium risk",
                className: "risk-medium"
            };
        }

        return {
            label: "Low risk",
            className: "risk-low"
        };
    }

    function getRouteAlertClass(flight) {
        const routeAlert = textOr(flight.route_alert, "clear").toLowerCase();

        if (
            routeAlert === "critical" ||
            routeAlert === "storm" ||
            routeAlert === "operational"
        ) {
            return {
                label: "Critical corridor",
                className: "route-alert-critical"
            };
        }

        if (
            routeAlert === "attention" ||
            routeAlert === "weather" ||
            routeAlert === "wind"
        ) {
            return {
                label: "Monitored corridor",
                className: "route-alert-warning"
            };
        }

        return {
            label: "Normal corridor",
            className: "route-alert-clear"
        };
    }

    function updateBadge(element, baseClass, className, label) {
        if (!element) {
            return;
        }

        element.className = baseClass + " " + className;
        element.textContent = label;
    }

    function updateSelectedPanel() {
        const selectedFlight = state.selectedFlightId
            ? getFlightById(state.selectedFlightId)
            : null;

        if (!selectedFlight) {
            setHidden(els.selectedFlightEmpty, false);
            setHidden(els.selectedFlightContent, true);
            return;
        }

        setHidden(els.selectedFlightEmpty, true);
        setHidden(els.selectedFlightContent, false);

        const priorityMeta = getPriorityMeta(selectedFlight);
        const riskMeta = getRiskClass(selectedFlight);
        const routeAlertMeta = getRouteAlertClass(selectedFlight);
        const status = normalizeStatus(selectedFlight.status);

        updateText(els.selectedFlightNumber, selectedFlight.flight_number);
        updateText(els.selectedFlightRouteText, formatRoute(selectedFlight));
        updateText(els.selectedFlightOriginCode, textOr(selectedFlight.origin_code, "N/A"));
        updateText(els.selectedFlightDestinationCode, textOr(selectedFlight.destination_code, "N/A"));

        updateBadge(
            els.selectedFlightPriorityBadge,
            "urgency-badge",
            priorityMeta.className,
            priorityMeta.label
        );

        updateBadge(
            els.selectedFlightStatusBadge,
            "status-badge",
            "status-" + status.replace(/_/g, "-"),
            toDisplayLabel(status)
        );

        updateBadge(
            els.selectedFlightRiskLevel,
            "risk-badge",
            riskMeta.className,
            riskMeta.label
        );

        updateBadge(
            els.selectedFlightRouteAlertBadge,
            "urgency-badge",
            routeAlertMeta.className,
            routeAlertMeta.label
        );

        updateText(els.selectedFlightAirline, textOr(selectedFlight.airline_name, "Airline unavailable"));
        updateText(els.selectedFlightAircraft, textOr(selectedFlight.aircraft_type, "Aircraft unavailable"));
        updateText(els.selectedFlightTrackingLabel, textOr(selectedFlight.tracking_label, toDisplayLabel(selectedFlight.tracking_mode || "Tracking")));
        updateText(els.selectedFlightEta, textOr(selectedFlight.eta, "ETA unavailable"));

        updateText(els.selectedFlightSource, textOr(selectedFlight.source, "Internal data"));
        updateText(els.selectedFlightProgress, Math.round(clamp(selectedFlight.progress, 0, 100)) + "%");
        updateText(els.selectedFlightRemainingDistance, formatDistance(selectedFlight.remaining_distance));
        updateText(els.selectedFlightFreshness, formatFreshness(selectedFlight));
        updateText(els.selectedFlightRiskScore, formatRiskScore(selectedFlight.risk_score));
        updateText(els.selectedFlightTracking, toDisplayLabel(selectedFlight.tracking_mode || "estimated"));

        setLink(els.selectedFlightDetailLink, selectedFlight.detail_url);
        setLink(els.selectedFlightMonitoringLink, selectedFlight.monitoring_url);
        setLink(els.selectedFlightMonitoringDetailLink, selectedFlight.monitoring_detail_url);
    }

    function updateCounters() {
        const visibleFlights = state.visibleFlights || [];

        const totalVisible = visibleFlights.length;

        const inAirVisible = visibleFlights.filter(function (flight) {
            return isInAirStatus(flight.status);
        }).length;

        const delayedVisible = visibleFlights.filter(function (flight) {
            return normalizeStatus(flight.status) === "delayed";
        }).length;

        const cancelledVisible = visibleFlights.filter(function (flight) {
            return normalizeStatus(flight.status) === "cancelled";
        }).length;

        const criticalVisible = visibleFlights.filter(isCriticalFlight).length;

        const disruptionScore = visibleFlights.reduce(function (total, flight) {
            const score = numberOrNull(flight.disruption_score);
            return total + (score || 0);
        }, 0);

        updateText(els.visibleFlightsCount, String(inAirVisible));
        updateText(els.filterCountAll, String(totalVisible));
        updateText(els.filterCountInAir, String(inAirVisible));
        updateText(els.filterCountDelayed, String(delayedVisible));
        updateText(els.mapStatsDelayedMirror, String(delayedVisible));
        updateText(els.filterCountCancelled, String(cancelledVisible));
        updateText(els.visibleCriticalCount, String(criticalVisible));
        updateText(els.visibleDisruptionScore, String(Math.round(disruptionScore)));
    }

    function updateCrisisBanner() {
        if (!els.mapCrisisModeLabel || !els.mapCrisisModeReason) {
            return;
        }

        const visibleFlights = state.visibleFlights || [];

        const delayedCount = visibleFlights.filter(function (flight) {
            return normalizeStatus(flight.status) === "delayed";
        }).length;

        const cancelledCount = visibleFlights.filter(function (flight) {
            return normalizeStatus(flight.status) === "cancelled";
        }).length;

        const criticalCount = visibleFlights.filter(isCriticalFlight).length;

        const hasOperationalWatch = cancelledCount > 0 ||
            delayedCount > 0 ||
            criticalCount > 0;

        if (hasOperationalWatch) {
            const parts = [];

            if (cancelledCount > 0) {
                parts.push(
                    cancelledCount + " cancelled " + (cancelledCount === 1 ? "flight" : "flights")
                );
            }

            if (delayedCount > 0) {
                parts.push(
                    delayedCount + " delayed " + (delayedCount === 1 ? "flight" : "flights")
                );
            }

            if (criticalCount > 0) {
                parts.push(
                    criticalCount + " critical " + (criticalCount === 1 ? "flight" : "flights")
                );
            }

            updateText(els.mapCrisisModeLabel, "OPERATIONAL WATCH");
            updateText(els.mapCrisisModeReason, parts.join(", ") + " visible on the map.");
            return;
        }

        updateText(els.mapCrisisModeLabel, "NORMAL OPERATIONS");
        updateText(els.mapCrisisModeReason, "No visible disruption pressure on the map.");
    }

    function toggleEmptyState() {
        if (!els.mapEmptyOverlay) {
            return;
        }

        const hasVisibleFlights = state.visibleFlights && state.visibleFlights.length > 0;

        els.mapEmptyOverlay.hidden = hasVisibleFlights;
        els.mapEmptyOverlay.classList.toggle("is-visible", !hasVisibleFlights);
    }

    function updateClock() {
        const now = new Date();
        const clockText = formatUtcClock(now);

        updateText(els.mapLiveClock, clockText);
        updateText(els.mapStatsClock, clockText);
    }

    function scheduleClock() {
        updateClock();

        if (state.clockTimer) {
            window.clearInterval(state.clockTimer);
        }

        state.clockTimer = window.setInterval(updateClock, 1000);
    }

    function scheduleRender() {
        if (state.renderTimer) {
            window.clearTimeout(state.renderTimer);
        }

        state.renderTimer = window.setTimeout(function () {
            renderFlights();
        }, RENDER_DEBOUNCE_MS);
    }

    function syncSearchInput(sourceElement) {
        const value = sourceElement ? sourceElement.value : "";

        state.searchQuery = value;

        if (els.mapSearchInput && els.mapSearchInput !== sourceElement) {
            els.mapSearchInput.value = value;
        }

        if (els.mapSearchInputMirror && els.mapSearchInputMirror !== sourceElement) {
            els.mapSearchInputMirror.value = value;
        }

        scheduleRender();
    }

    function setToolsPanel(open) {
        state.toolsPanelOpen = Boolean(open);

        if (els.mapToolsPanel) {
            els.mapToolsPanel.classList.toggle("is-open", state.toolsPanelOpen);
            els.mapToolsPanel.setAttribute("aria-hidden", state.toolsPanelOpen ? "false" : "true");
        }

        if (els.toggleToolsPanelBtn) {
            els.toggleToolsPanelBtn.classList.toggle("is-active", state.toolsPanelOpen);
            els.toggleToolsPanelBtn.setAttribute("aria-expanded", state.toolsPanelOpen ? "true" : "false");
        }
    }

    function locateUser() {
        if (!state.map || !navigator.geolocation) {
            updateText(els.mapLocationText, "Location unavailable");
            return;
        }

        updateText(els.mapLocationText, "Locating operator...");

        navigator.geolocation.getCurrentPosition(
            function (position) {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;

                if (state.userMarker) {
                    state.map.removeLayer(state.userMarker);
                }

                state.userMarker = L.circleMarker([lat, lng], {
                    radius: 7,
                    color: "#3b82f6",
                    weight: 2,
                    fillColor: "#60a5fa",
                    fillOpacity: 0.38
                }).addTo(state.map);

                state.userMarker.bindTooltip("Operator location", {
                    direction: "top",
                    className: "logosflight-location-tooltip"
                });

                state.map.setView([lat, lng], Math.max(state.map.getZoom(), 6), {
                    animate: true
                });

                updateText(els.mapLocationText, "Operator location active");
            },
            function () {
                updateText(els.mapLocationText, "Location permission unavailable");
            },
            {
                enableHighAccuracy: true,
                timeout: 8000,
                maximumAge: 30000
            }
        );
    }

    function setCoverageStatus() {
        if (els.mapRefreshState) {
            els.mapRefreshState.textContent = "Layer";
        }

        if (els.mapRefreshStateText) {
            els.mapRefreshStateText.textContent = "Live + estimated coverage";
        }
    }

    function refreshOperationalMap() {
        if (state.isRefreshing) {
            return;
        }

        state.isRefreshing = true;

        if (els.mapRefreshLabel) {
            els.mapRefreshLabel.textContent = "Refreshing...";
        }

        if (els.mapRefreshIcon) {
            els.mapRefreshIcon.classList.add("is-spinning");
        }

        if (els.mapRefreshState) {
            els.mapRefreshState.textContent = "Sync";
        }

        if (els.mapRefreshStateText) {
            els.mapRefreshStateText.textContent = "Refreshing map";
        }

        loadFlights();
        renderFlights();
        setReferenceView();

        refreshBackendWeather().finally(function () {
            window.setTimeout(function () {
                state.isRefreshing = false;

                if (els.mapRefreshLabel) {
                    els.mapRefreshLabel.textContent = "Refresh map";
                }

                if (els.mapRefreshIcon) {
                    els.mapRefreshIcon.classList.remove("is-spinning");
                }

                setCoverageStatus();
            }, REFRESH_UI_DELAY_MS);
        });
    }

    function resetMapView() {
        setReferenceView();
    }

    function toggleFullscreen() {
        const stage = byId("mapStageShell") || els["flight-map"];

        if (!stage) {
            return;
        }

        if (!document.fullscreenElement) {
            stage.requestFullscreen().catch(function (error) {
                console.warn("Fullscreen request failed:", error);
            });
            return;
        }

        document.exitFullscreen().catch(function (error) {
            console.warn("Fullscreen exit failed:", error);
        });
    }

    function bindLayerToggle(button, key) {
        if (!button) {
            return;
        }

        button.addEventListener("click", function () {
            state.toggles[key] = !state.toggles[key];
            button.classList.toggle("is-active", state.toggles[key]);
            button.setAttribute("aria-pressed", state.toggles[key] ? "true" : "false");

            if (key === "weather") {
                if (state.toggles.weather) {
                    refreshBackendWeather();
                } else {
                    removeRadarLayer();
                    renderWeatherHazards(null);
                    updateWeatherPanel(null);
                }
            }

            scheduleRender();
        });

        button.classList.toggle("is-active", state.toggles[key]);
        button.setAttribute("aria-pressed", state.toggles[key] ? "true" : "false");
    }

    function bindEvents() {
        if (els.mapSearchInput) {
            els.mapSearchInput.addEventListener("input", function () {
                syncSearchInput(els.mapSearchInput);
            });
        }

        if (els.mapSearchInputMirror) {
            els.mapSearchInputMirror.addEventListener("input", function () {
                syncSearchInput(els.mapSearchInputMirror);
            });
        }

        if (els.mapStatusSelect) {
            els.mapStatusSelect.addEventListener("change", function () {
                state.statusFilter = textOr(els.mapStatusSelect.value, "all");
                scheduleRender();
            });
        }

        if (els.baseLayerSelect) {
            els.baseLayerSelect.addEventListener("change", function () {
                setBaseLayer(els.baseLayerSelect.value);
            });
        }

        if (els.weatherLayerSelect) {
            els.weatherLayerSelect.addEventListener("change", function () {
                state.weatherLayerKey = normalizeLayerValue(els.weatherLayerSelect.value);

                if (shouldDisplayWeatherLayer()) {
                    refreshBackendWeather();
                } else {
                    removeRadarLayer();
                    updateWeatherPanel(null);
                }

                scheduleRender();
            });
        }

        bindLayerToggle(els.toggleAircraft, "aircraft");
        bindLayerToggle(els.toggleRoutes, "routes");
        bindLayerToggle(els.toggleAirports, "airports");
        bindLayerToggle(els.toggleLabels, "labels");
        bindLayerToggle(els.toggleWeather, "weather");
        bindLayerToggle(els.toggleRestrictedZones, "restrictedZones");
        bindLayerToggle(els.toggleAlertZones, "alertZones");

        if (els.criticalOnlyBtn) {
            els.criticalOnlyBtn.addEventListener("click", function () {
                state.toggles.criticalOnly = !state.toggles.criticalOnly;
                els.criticalOnlyBtn.classList.toggle("is-active", state.toggles.criticalOnly);
                els.criticalOnlyBtn.setAttribute("aria-pressed", state.toggles.criticalOnly ? "true" : "false");
                scheduleRender();
            });
        }

        if (els.resetMapViewBtn) {
            els.resetMapViewBtn.addEventListener("click", function () {
                refreshOperationalMap();
            });
        }

        if (els.toggleFullscreenBtn) {
            els.toggleFullscreenBtn.addEventListener("click", toggleFullscreen);
        }

        if (els.toggleFullscreenBtnPanel) {
            els.toggleFullscreenBtnPanel.addEventListener("click", toggleFullscreen);
        }

        if (els.toggleToolsPanelBtn) {
            els.toggleToolsPanelBtn.addEventListener("click", function () {
                setToolsPanel(!state.toolsPanelOpen);
            });
        }

        if (els.closeToolsPanelBtn) {
            els.closeToolsPanelBtn.addEventListener("click", function () {
                setToolsPanel(false);
            });
        }

        if (els.clearSelectedFlightBtn) {
            els.clearSelectedFlightBtn.addEventListener("click", clearSelectedFlight);
        }

        if (els.locateMeBtn) {
            els.locateMeBtn.addEventListener("click", locateUser);
        }

        [els.focusSelectedBtn, els.focusSelectedBtnPanel, els.focusSelectedBtnDrawer].forEach(function (button) {
            if (!button) {
                return;
            }

            button.addEventListener("click", focusSelectedFlight);
        });

        document.addEventListener("click", function (event) {
            const target = event.target.closest("[data-flight-select]");

            if (!target) {
                return;
            }

            const flightId = target.getAttribute("data-flight-select");

            if (flightId) {
                selectFlight(flightId, {
                    focus: true
                });
            }
        });

        document.addEventListener("fullscreenchange", function () {
            const stage = byId("mapStageShell");

            state.fullscreen = Boolean(document.fullscreenElement);

            if (stage) {
                stage.classList.toggle("is-fullscreen", state.fullscreen);
            }

            window.setTimeout(function () {
                if (state.map) {
                    state.map.invalidateSize(false);
                }
            }, 150);
        });

        const themeObserver = new MutationObserver(syncThemeClass);

        themeObserver.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ["class", "data-theme"]
        });

        themeObserver.observe(document.body, {
            attributes: true,
            attributeFilter: ["class", "data-theme"]
        });

        window.addEventListener("resize", function () {
            if (state.map) {
                state.map.invalidateSize(false);
            }
        });
    }

    function initialize() {
        collectElements();

        if (!els["flight-map"]) {
            return;
        }

        syncThemeClass();
        loadFlights();
        initializeMap();
        bindEvents();
        scheduleClock();
        setCoverageStatus();

        renderFlights();

        window.setTimeout(function () {
            setReferenceView();

            if (state.selectedFlightId) {
                focusSelectedFlight();
            }

            setCoverageStatus();
        }, 180);

        scheduleBackendWeatherRefresh();
    }

    initialize();
});