from apps.copilot.constants import (
    COPILOT_CONFIDENCE,
    COPILOT_INTENTS,
    COPILOT_RESPONSE_TYPES,
    COPILOT_SUPPORTED_METRICS,
)
from apps.copilot.repositories.flight_queries import FlightQueries
from apps.copilot.repositories.sync_queries import SyncQueries
from apps.copilot.services.copilot_answer_rewriter import CopilotAnswerRewriter
from apps.copilot.services.intent_detector import IntentDetector
from apps.copilot.services.language_service import CopilotLanguageService
from apps.copilot.services.response_builder import ResponseBuilder
from apps.copilot.services.system_snapshot_service import SystemSnapshotService


class CopilotService:
    """
    Main service for the Operational Copilot module.

    It detects the user's intent, reads the required project data and returns
    a structured response for the frontend interface.
    """

    def __init__(self):
        self.intent_detector = IntentDetector()
        self.language_service = CopilotLanguageService()
        self.response_builder = ResponseBuilder()
        self.answer_rewriter = CopilotAnswerRewriter()

        self.flight_queries = FlightQueries()
        self.sync_queries = SyncQueries()

        self.system_snapshot_service = SystemSnapshotService(
            flight_queries=self.flight_queries,
            sync_queries=self.sync_queries,
        )

    def handle_message(self, message: str, interface_language: str | None = None) -> dict:
        try:
            raw_message = (message or "").strip()

            if interface_language in ["en", "fr", "ru"]:
                language = interface_language
            else:
                language = self.language_service.detect_language(raw_message)

            if not raw_message:
                return self._finalize(self._handle_empty_message(language))

            forced_intent = self._detect_forced_multilingual_intent(raw_message)

            if forced_intent:
                payload = {
                    "intent": forced_intent,
                    "metric_key": None,
                    "extracted_value": None,
                    "normalized_message": raw_message.lower().strip(),
                }
            else:
                payload = self.intent_detector.detect(raw_message)

            intent = payload.get("intent")
            metric_key = payload.get("metric_key")
            extracted_value = payload.get("extracted_value")
            normalized_message = payload.get("normalized_message") or ""

            if intent == "COPILOT_GREETING":
                return self._finalize(self._handle_greeting(language))

            if intent == "DATABASE_DICTIONARY" or self._is_database_dictionary_query(normalized_message):
                return self._finalize(self._handle_database_dictionary(language))

            if intent == "TOP_AIRLINE":
                return self._finalize(self._handle_top_airline(language))

            if intent == "TOP_AIRPORT":
                return self._finalize(self._handle_top_airport(language))

            if intent == "TOP_ROUTE":
                return self._finalize(self._handle_top_route(language))

            if intent == "TODAYS_FLIGHTS":
                return self._finalize(self._handle_todays_flights(language))

            if intent == "FLIGHTS_BY_STATUS":
                return self._finalize(self._handle_flights_by_status(extracted_value, language))

            if intent == "FLIGHTS_BY_AIRLINE":
                return self._finalize(self._handle_flights_by_airline(extracted_value, language))

            if intent == COPILOT_INTENTS["OPERATIONAL_SUMMARY"]:
                return self._finalize(self._handle_operational_summary(language))

            if intent == COPILOT_INTENTS["DELAYED_FLIGHTS"]:
                return self._finalize(self._handle_delayed_flights(language))

            if intent == COPILOT_INTENTS["CANCELLED_FLIGHTS"]:
                return self._finalize(self._handle_cancelled_flights(language))

            if intent == COPILOT_INTENTS["PRIORITY_FLIGHTS"]:
                return self._finalize(self._handle_priority_flights(language))

            if intent == COPILOT_INTENTS["API_SYNC_STATUS"]:
                return self._finalize(self._handle_api_sync_status(language))

            if intent == COPILOT_INTENTS["MODULE_ROUTING"]:
                return self._finalize(self._handle_module_routing(language))

            if intent == COPILOT_INTENTS["SOURCE_BREAKDOWN"]:
                return self._finalize(self._handle_source_breakdown(language))

            if intent == COPILOT_INTENTS["CRITICAL_ATTENTION"]:
                return self._finalize(self._handle_critical_attention(language))

            if intent == COPILOT_INTENTS["EXPLAIN_METRIC"]:
                return self._finalize(self._handle_explain_metric(metric_key, language))

            return self._finalize(self._handle_unknown(raw_message, language))

        except Exception:
            return self._finalize(
                self.response_builder.build_system_message(
                    intent=COPILOT_INTENTS["UNKNOWN"],
                    title="Request unavailable",
                    message="The system could not complete this request. Please try again with a more specific operational question.",
                )
            )

    def _finalize(self, business_response: dict) -> dict:
        if not business_response:
            return business_response

        business_response["rewritten_message"] = None

        original_message = business_response.get("message") or ""
        language = self._detect_response_language(original_message)

        rewrite_result = self.answer_rewriter.rewrite(
            original_message=original_message,
            language=language,
            title=business_response.get("title") or "",
            bullets=business_response.get("bullets") or [],
            metrics=business_response.get("metrics") or {},
            response_type=business_response.get("type") or "",
            intent=business_response.get("intent") or "",
        )

        if rewrite_result.ok:
            business_response["rewritten_message"] = rewrite_result.text
            business_response["rewrite_source"] = "local_refinement"
        else:
            business_response["rewrite_source"] = "original"
            business_response["rewrite_error"] = rewrite_result.error

        return business_response

    def _detect_response_language(self, text: str) -> str:
        value = (text or "").lower()

        if any("\u0400" <= char <= "\u04ff" for char in value):
            return "ru"

        french_markers = [
            "bonjour",
            "je ",
            "j'ai",
            "le système",
            "le systeme",
            "vol",
            "vols",
            "retard",
            "annulé",
            "annules",
            "opération",
            "operation",
            "synchronisation",
            "données",
            "donnees",
        ]

        if any(marker in value for marker in french_markers):
            return "fr"

        return "en"

    def _handle_empty_message(self, language: str = "en") -> dict:
        return self.response_builder.build_unavailable(
            intent=COPILOT_INTENTS["UNKNOWN"],
            title=self.language_service.text("empty_title", language),
            message=self.language_service.text("empty_request", language),
        )

    def _handle_greeting(self, language: str = "en") -> dict:
        snapshot = self.system_snapshot_service.build_snapshot()
        summary = snapshot["flight_summary"]

        total_flights = summary.get("total_flights", 0)
        active_count = summary.get("active_count", 0)
        delayed_count = summary.get("delayed_count", 0)
        cancelled_count = summary.get("cancelled_count", 0)

        return self.response_builder.build(
            response_type=COPILOT_RESPONSE_TYPES["EXPLANATORY"],
            intent="COPILOT_GREETING",
            title=self.language_service.text("greeting_title", language),
            message=self.language_service.text("greeting_message", language),
            bullets=[
                self.language_service.text(
                    "greeting_bullet_total",
                    language,
                    total_flights=total_flights,
                ),
                self.language_service.text(
                    "greeting_bullet_active",
                    language,
                    active_count=active_count,
                ),
                self.language_service.text(
                    "greeting_bullet_delayed",
                    language,
                    delayed_count=delayed_count,
                ),
                self.language_service.text(
                    "greeting_bullet_cancelled",
                    language,
                    cancelled_count=cancelled_count,
                ),
                self.language_service.text("greeting_bullet_scope", language),
            ],
            metrics={
                "total_flights": total_flights,
                "active_count": active_count,
                "delayed_count": delayed_count,
                "cancelled_count": cancelled_count,
            },
            recommended_module="Operations Center",
            recommended_url="/dashboard/",
            confidence=COPILOT_CONFIDENCE["HIGH"],
            source_note="This response is based on the current Flight repository snapshot.",
            suggested_prompts=[
                "Give me the current operational summary.",
                "Which flights need attention?",
                "What is the API sync status?",
                "Show delayed flights.",
            ],
        )

    def _handle_operational_summary(self, language: str = "en") -> dict:
        snapshot = self.system_snapshot_service.build_snapshot()
        summary = snapshot["flight_summary"]

        total_flights = summary.get("total_flights", 0)
        active_count = summary.get("active_count", 0)
        delayed_count = summary.get("delayed_count", 0)
        cancelled_count = summary.get("cancelled_count", 0)
        live_tracked_count = summary.get("live_tracked_count", 0)
        dominant_status = summary.get("dominant_status") or "not available"
        critical_count = summary.get("critical_count", 0)

        if total_flights == 0:
            return self.response_builder.build(
                response_type=COPILOT_RESPONSE_TYPES["DATA_BASED"],
                intent=COPILOT_INTENTS["OPERATIONAL_SUMMARY"],
                title=self.language_service.text("operational_summary_title", language),
                message=self.language_service.text("operational_summary_no_data", language),
                metrics=summary,
                recommended_module="Data Sync",
                recommended_url="/sync/",
                confidence=COPILOT_CONFIDENCE["MEDIUM"],
                source_note="This response is based on the internal Flight repository.",
            )

        if critical_count > 0:
            message = self.language_service.text(
                "operational_summary_message_attention",
                language,
                total_flights=total_flights,
                active_count=active_count,
                critical_count=critical_count,
            )
            situation = self.language_service.text("situation_pressure", language)
            recommended_module = "Monitoring Map"
            recommended_url = "/monitoring/map/"
        else:
            message = self.language_service.text(
                "operational_summary_message_stable",
                language,
                total_flights=total_flights,
                active_count=active_count,
            )
            situation = self.language_service.text("situation_stable", language)
            recommended_module = "Operations Center"
            recommended_url = "/dashboard/"

        return self.response_builder.build(
            response_type=COPILOT_RESPONSE_TYPES["DATA_BASED"],
            intent=COPILOT_INTENTS["OPERATIONAL_SUMMARY"],
            title=self.language_service.text("operational_summary_title", language),
            message=message,
            bullets=[
                situation,
                self.language_service.text(
                    "delayed_count",
                    language,
                    delayed_count=delayed_count,
                ),
                self.language_service.text(
                    "cancelled_count",
                    language,
                    cancelled_count=cancelled_count,
                ),
                self.language_service.text(
                    "live_tracked_count",
                    language,
                    live_tracked_count=live_tracked_count,
                ),
                self.language_service.text(
                    "dominant_status",
                    language,
                    dominant_status=dominant_status,
                ),
                self.language_service.text(
                    "delay_rate",
                    language,
                    delay_rate=summary.get("delay_rate", 0),
                ),
                self.language_service.text(
                    "cancellation_rate",
                    language,
                    cancellation_rate=summary.get("cancellation_rate", 0),
                ),
                self.language_service.text("stored_data_note", language),
            ],
            metrics=summary,
            recommended_module=recommended_module,
            recommended_url=recommended_url,
            confidence=COPILOT_CONFIDENCE["HIGH"],
            source_note="This response is based on the internal Flight repository snapshot.",
        )

    def _handle_delayed_flights(self, language: str = "en") -> dict:
        records = self.flight_queries.get_delayed_flights(limit=10)
        total_count = self.flight_queries.count_flights_by_status("delayed")

        if not records:
            return self.response_builder.build(
                response_type=COPILOT_RESPONSE_TYPES["DATA_BASED"],
                intent=COPILOT_INTENTS["DELAYED_FLIGHTS"],
                title=self.language_service.text("delayed_title", language),
                message=self.language_service.text("delayed_none", language),
                metrics={"delayed_count": 0},
                records=[],
                recommended_module="Data Sync",
                recommended_url="/sync/",
                confidence=COPILOT_CONFIDENCE["HIGH"],
                source_note="This response is based on the Flight status filter.",
            )

        return self.response_builder.build(
            response_type=COPILOT_RESPONSE_TYPES["DATA_BASED"],
            intent=COPILOT_INTENTS["DELAYED_FLIGHTS"],
            title=self.language_service.text("delayed_title", language),
            message=self.language_service.text(
                "delayed_found",
                language,
                total_count=total_count,
            ),
            bullets=[
                self.language_service.text(
                    "stored_data_note",
                    language,
                ),
            ],
            metrics={"delayed_count": total_count},
            records=records,
            recommended_module="Monitoring Map",
            recommended_url="/monitoring/map/",
            confidence=COPILOT_CONFIDENCE["HIGH"],
            source_note="This response is based on the Flight status filter.",
        )

    def _handle_cancelled_flights(self, language: str = "en") -> dict:
        records = self.flight_queries.get_cancelled_flights(limit=10)
        total_count = self.flight_queries.count_flights_by_status("cancelled")

        if not records:
            return self.response_builder.build(
                response_type=COPILOT_RESPONSE_TYPES["DATA_BASED"],
                intent=COPILOT_INTENTS["CANCELLED_FLIGHTS"],
                title=self.language_service.text("cancelled_title", language),
                message=self.language_service.text("cancelled_none", language),
                metrics={"cancelled_count": 0},
                records=[],
                recommended_module="Flights",
                recommended_url="/flights/",
                confidence=COPILOT_CONFIDENCE["HIGH"],
                source_note="This response is based on the Flight status filter.",
            )

        return self.response_builder.build(
            response_type=COPILOT_RESPONSE_TYPES["DATA_BASED"],
            intent=COPILOT_INTENTS["CANCELLED_FLIGHTS"],
            title=self.language_service.text("cancelled_title", language),
            message=self.language_service.text(
                "cancelled_found",
                language,
                total_count=total_count,
            ),
            bullets=[
                self.language_service.text(
                    "stored_data_note",
                    language,
                ),
            ],
            metrics={"cancelled_count": total_count},
            records=records,
            recommended_module="Monitoring Map",
            recommended_url="/monitoring/map/",
            confidence=COPILOT_CONFIDENCE["HIGH"],
            source_note="This response is based on the Flight status filter.",
        )

    def _handle_priority_flights(self, language: str = "en") -> dict:
        records = self.flight_queries.get_priority_flights(limit=10)

        if not records:
            return self.response_builder.build(
                response_type=COPILOT_RESPONSE_TYPES["DATA_BASED"],
                intent=COPILOT_INTENTS["PRIORITY_FLIGHTS"],
                title=self.language_service.text("priority_title", language),
                message=self.language_service.text("priority_none", language),
                metrics={"critical_count": 0},
                records=[],
                recommended_module="Operations Center",
                recommended_url="/dashboard/",
                confidence=COPILOT_CONFIDENCE["HIGH"],
                source_note="Priority logic is currently based on delayed and cancelled flights.",
            )

        cancelled_count = len([record for record in records if record.get("status") == "cancelled"])
        delayed_count = len([record for record in records if record.get("status") == "delayed"])

        return self.response_builder.build(
            response_type=COPILOT_RESPONSE_TYPES["DATA_BASED"],
            intent=COPILOT_INTENTS["PRIORITY_FLIGHTS"],
            title=self.language_service.text("priority_title", language),
            message=self.language_service.text(
                "priority_found",
                language,
                count=len(records),
            ),
            bullets=[
                self.language_service.text(
                    "cancelled_count",
                    language,
                    cancelled_count=cancelled_count,
                ),
                self.language_service.text(
                    "delayed_count",
                    language,
                    delayed_count=delayed_count,
                ),
            ],
            metrics={
                "critical_count": len(records),
                "cancelled_count": cancelled_count,
                "delayed_count": delayed_count,
            },
            records=records,
            recommended_module="Monitoring Map",
            recommended_url="/monitoring/map/",
            confidence=COPILOT_CONFIDENCE["HIGH"],
            source_note="Priority logic is currently based on delayed and cancelled flights.",
        )

    def _handle_api_sync_status(self, language: str = "en") -> dict:
        summary = self.sync_queries.get_sync_status_summary()
        latest_log = summary.get("latest_log")
        last_successful_log = summary.get("last_successful_log")

        if not latest_log:
            return self.response_builder.build(
                response_type=COPILOT_RESPONSE_TYPES["DATA_BASED"],
                intent=COPILOT_INTENTS["API_SYNC_STATUS"],
                title=self.language_service.text("api_sync_title", language),
                message=self.language_service.text("api_sync_no_log", language),
                metrics=summary,
                records=[],
                recommended_module="Data Sync",
                recommended_url="/sync/",
                confidence=COPILOT_CONFIDENCE["LOW"],
                source_note="This response is based on ApiSyncLog records.",
            )

        latest_status = latest_log.get("status_label", "Unknown")
        latest_provider = latest_log.get("provider_name", "Unknown provider")
        latest_sync_type = latest_log.get("sync_type", "Unknown sync type")

        if latest_log.get("status") == "failed":
            message = self.language_service.text(
                "api_sync_failed",
                language,
                latest_provider=latest_provider,
                latest_sync_type=latest_sync_type,
                latest_status=latest_status,
            )
            confidence = COPILOT_CONFIDENCE["MEDIUM"]
        else:
            message = self.language_service.text(
                "api_sync_success",
                language,
                latest_provider=latest_provider,
                latest_status=latest_status,
            )
            confidence = COPILOT_CONFIDENCE["HIGH"]

        bullets = [
            f"Provider: {latest_provider}.",
            f"Sync type: {latest_sync_type}.",
            f"Latest status: {latest_status}.",
            f"Success rate: {summary.get('success_rate', 0)}%.",
            f"Review rate: {summary.get('failure_rate', 0)}%.",
            f"Failed logs: {summary.get('failed_count', 0)}.",
            f"Records received: {summary.get('total_records_received', 0)}.",
            f"Records updated: {summary.get('total_records_updated', 0)}.",
        ]

        if last_successful_log:
            bullets.append(f"Last successful sync: {last_successful_log.get('started_at')}.")

        return self.response_builder.build(
            response_type=COPILOT_RESPONSE_TYPES["DATA_BASED"],
            intent=COPILOT_INTENTS["API_SYNC_STATUS"],
            title=self.language_service.text("api_sync_title", language),
            message=message,
            bullets=bullets,
            metrics=summary,
            records=self.sync_queries.get_recent_logs(limit=5),
            recommended_module="Data Sync",
            recommended_url="/sync/",
            confidence=confidence,
            source_note="This response separates the latest sync result from historical sync-log statistics.",
        )

    def _handle_module_routing(self, language: str = "en") -> dict:
        snapshot = self.system_snapshot_service.build_snapshot()
        summary = snapshot["flight_summary"]
        sync_summary = snapshot["api_sync_status"]

        critical_count = summary.get("critical_count", 0)
        delayed_count = summary.get("delayed_count", 0)
        cancelled_count = summary.get("cancelled_count", 0)
        failed_sync_count = sync_summary.get("failed_count", 0)

        if critical_count > 0:
            recommended_module = "Monitoring Map"
            recommended_url = "/monitoring/map/"
        elif failed_sync_count > 0:
            recommended_module = "Data Sync"
            recommended_url = "/sync/"
        else:
            recommended_module = "Operations Center"
            recommended_url = "/dashboard/"

        return self.response_builder.build(
            response_type=COPILOT_RESPONSE_TYPES["EXPLANATORY"],
            intent=COPILOT_INTENTS["MODULE_ROUTING"],
            title="Recommended module",
            message=f"Recommended module: {recommended_module}.",
            bullets=[
                self.language_service.text("delayed_count", language, delayed_count=delayed_count),
                self.language_service.text("cancelled_count", language, cancelled_count=cancelled_count),
                f"Sync logs needing review: {failed_sync_count}.",
            ],
            metrics={
                "delayed_count": delayed_count,
                "cancelled_count": cancelled_count,
                "failed_count": failed_sync_count,
            },
            recommended_module=recommended_module,
            recommended_url=recommended_url,
            confidence=COPILOT_CONFIDENCE["HIGH"],
            source_note="This recommendation is based on the current system snapshot.",
        )

    def _handle_source_breakdown(self, language: str = "en") -> dict:
        breakdown = self.flight_queries.get_source_breakdown()

        api_flights = breakdown.get("api_flights", 0)
        local_flights = breakdown.get("local_flights", 0)

        if breakdown.get("total_flights", 0) == 0:
            message = "Source distribution cannot be calculated because no flight records are currently available."
        elif api_flights > local_flights:
            message = f"The current flight base is mainly provider-driven: {api_flights} API records and {local_flights} local records."
        elif local_flights > api_flights:
            message = f"The current flight base is mainly local: {local_flights} local records and {api_flights} API records."
        else:
            message = f"The current flight base is balanced: {api_flights} API records and {local_flights} local records."

        return self.response_builder.build(
            response_type=COPILOT_RESPONSE_TYPES["DATA_BASED"],
            intent=COPILOT_INTENTS["SOURCE_BREAKDOWN"],
            title=self.language_service.text("source_breakdown_title", language),
            message=message,
            bullets=[
                f"API share: {breakdown.get('api_rate', 0)}%.",
                f"Local share: {breakdown.get('local_rate', 0)}%.",
            ],
            metrics=breakdown,
            recommended_module="Operational Intelligence",
            recommended_url="/analytics/",
            confidence=COPILOT_CONFIDENCE["HIGH"],
            source_note="This response is based on the Flight source_type field.",
        )

    def _handle_critical_attention(self, language: str = "en") -> dict:
        snapshot = self.flight_queries.get_critical_attention_snapshot(limit=5)

        critical_count = snapshot.get("critical_count", 0)
        delayed_count = snapshot.get("delayed_count", 0)
        cancelled_count = snapshot.get("cancelled_count", 0)
        priority_flights = snapshot.get("priority_flights", [])

        if critical_count == 0:
            message = "No critical attention signal is currently visible in the system."
        else:
            message = (
                f"{critical_count} flights currently require operational attention: "
                f"{delayed_count} delayed and {cancelled_count} cancelled."
            )

        return self.response_builder.build(
            response_type=COPILOT_RESPONSE_TYPES["DATA_BASED"],
            intent=COPILOT_INTENTS["CRITICAL_ATTENTION"],
            title=self.language_service.text("critical_title", language),
            message=message,
            bullets=[
                self.language_service.text("delayed_count", language, delayed_count=delayed_count),
                self.language_service.text("cancelled_count", language, cancelled_count=cancelled_count),
            ],
            metrics={
                "critical_count": critical_count,
                "delayed_count": delayed_count,
                "cancelled_count": cancelled_count,
            },
            records=priority_flights,
            recommended_module="Monitoring Map" if critical_count else "Operations Center",
            recommended_url="/monitoring/map/" if critical_count else "/dashboard/",
            confidence=COPILOT_CONFIDENCE["HIGH"],
            source_note="Critical attention is currently based on delayed and cancelled flights.",
        )

    def _handle_explain_metric(self, metric_key: str | None, language: str = "en") -> dict:
        metric_label = "metric"

        if metric_key:
            metric_label = COPILOT_SUPPORTED_METRICS.get(metric_key, {}).get(
                "label",
                metric_key,
            )

        return self.response_builder.build(
            response_type=COPILOT_RESPONSE_TYPES["EXPLANATORY"],
            intent=COPILOT_INTENTS["EXPLAIN_METRIC"],
            title="Metric explanation",
            message=f"This metric explains: {metric_label}.",
            metrics={
                "metric_key": metric_key or "unknown",
                "metric_label": metric_label,
            },
            confidence=COPILOT_CONFIDENCE["HIGH"],
            source_note="This answer is based on the project metric definitions.",
        )

    def _handle_top_airline(self, language: str = "en") -> dict:
        top_airlines = self.flight_queries.get_top_airlines(limit=5)

        if not top_airlines:
            return self.response_builder.build(
                response_type=COPILOT_RESPONSE_TYPES["DATA_BASED"],
                intent="TOP_AIRLINE",
                title="Top airline by flight volume",
                message="A leading airline cannot be identified because no airline-linked flight records are available.",
                records=[],
                recommended_module="Airlines",
                recommended_url="/airlines/",
                confidence=COPILOT_CONFIDENCE["MEDIUM"],
                source_note="This response is based on current Flight and Airline relationships.",
            )

        leader = top_airlines[0]

        records = [
            {
                "flight_number": item["airline_name"],
                "route": f"{item['flight_count']} flights",
                "status_label": "Traffic volume",
                "source_type_label": "Aggregated",
            }
            for item in top_airlines
        ]

        return self.response_builder.build(
            response_type=COPILOT_RESPONSE_TYPES["DATA_BASED"],
            intent="TOP_AIRLINE",
            title="Top airline by flight volume",
            message=(
                f"{leader['airline_name']} currently has the highest flight volume "
                f"with {leader['flight_count']} flights in the system."
            ),
            records=records,
            recommended_module="Airlines",
            recommended_url="/airlines/",
            confidence=COPILOT_CONFIDENCE["HIGH"],
            source_note="This response is based on current Flight and Airline relationships.",
        )

    def _handle_top_airport(self, language: str = "en") -> dict:
        top_airports = self.flight_queries.get_top_airports(limit=5)

        if not top_airports:
            return self.response_builder.build(
                response_type=COPILOT_RESPONSE_TYPES["DATA_BASED"],
                intent="TOP_AIRPORT",
                title="Top airport by flight volume",
                message="A leading airport cannot be identified because no origin-airport flight records are available.",
                records=[],
                recommended_module="Airports",
                recommended_url="/airports/",
                confidence=COPILOT_CONFIDENCE["MEDIUM"],
                source_note="This response is based on origin airport distribution.",
            )

        leader = top_airports[0]
        leader_display = leader["airport_name"]

        if leader.get("airport_code"):
            leader_display = f"{leader['airport_name']} ({leader['airport_code']})"

        records = [
            {
                "flight_number": (
                    f"{item['airport_name']} ({item['airport_code']})"
                    if item.get("airport_code")
                    else item["airport_name"]
                ),
                "route": f"{item['flight_count']} flights",
                "status_label": "Traffic volume",
                "source_type_label": "Aggregated",
            }
            for item in top_airports
        ]

        return self.response_builder.build(
            response_type=COPILOT_RESPONSE_TYPES["DATA_BASED"],
            intent="TOP_AIRPORT",
            title="Top airport by flight volume",
            message=(
                f"{leader_display} currently has the highest origin traffic "
                f"with {leader['flight_count']} flights."
            ),
            records=records,
            recommended_module="Airports",
            recommended_url="/airports/",
            confidence=COPILOT_CONFIDENCE["HIGH"],
            source_note="This response is based on origin airport distribution.",
        )

    def _handle_top_route(self, language: str = "en") -> dict:
        top_routes = self.flight_queries.get_top_routes(limit=5)

        if not top_routes:
            return self.response_builder.build(
                response_type=COPILOT_RESPONSE_TYPES["DATA_BASED"],
                intent="TOP_ROUTE",
                title="Top route by flight volume",
                message="A leading route cannot be identified because complete origin and destination links are missing.",
                records=[],
                recommended_module="Flights",
                recommended_url="/flights/",
                confidence=COPILOT_CONFIDENCE["MEDIUM"],
                source_note="This response is based on origin and destination route aggregation.",
            )

        leader = top_routes[0]

        records = [
            {
                "flight_number": item["route"],
                "route": f"{item['flight_count']} flights",
                "status_label": "Traffic volume",
                "source_type_label": "Aggregated",
            }
            for item in top_routes
        ]

        return self.response_builder.build(
            response_type=COPILOT_RESPONSE_TYPES["DATA_BASED"],
            intent="TOP_ROUTE",
            title="Top route by flight volume",
            message=(
                f"{leader['route']} is currently the busiest route "
                f"with {leader['flight_count']} flights in the system."
            ),
            records=records,
            recommended_module="Operational Intelligence",
            recommended_url="/analytics/routes/",
            confidence=COPILOT_CONFIDENCE["HIGH"],
            source_note="This response is based on origin and destination route aggregation.",
        )

    def _handle_todays_flights(self, language: str = "en") -> dict:
        total_count = self.flight_queries.count_todays_flights()
        records = self.flight_queries.get_todays_flights(limit=15)

        return self.response_builder.build(
            response_type=COPILOT_RESPONSE_TYPES["DATA_BASED"],
            intent="TODAYS_FLIGHTS",
            title="Today's flights",
            message=f"{total_count} flights are scheduled for today in the system.",
            metrics={"total_flights": total_count},
            records=records,
            recommended_module="Flights",
            recommended_url="/flights/",
            confidence=COPILOT_CONFIDENCE["HIGH"],
            source_note="This response is based on scheduled departure date.",
        )

    def _handle_flights_by_status(self, status: str | None, language: str = "en") -> dict:
        if not status:
            return self._handle_unknown("", language)

        total_count = self.flight_queries.count_flights_by_status(status)
        records = self.flight_queries.get_flights_by_status(status=status, limit=15)
        status_label = status.replace("_", " ").title()

        return self.response_builder.build(
            response_type=COPILOT_RESPONSE_TYPES["DATA_BASED"],
            intent="FLIGHTS_BY_STATUS",
            title=f"{status_label} flights",
            message=f"I found {total_count} {status_label.lower()} flights in the system.",
            metrics={f"{status}_count": total_count},
            records=records,
            recommended_module="Flights",
            recommended_url="/flights/",
            confidence=COPILOT_CONFIDENCE["HIGH"],
            source_note="This response is based on Flight status filtering.",
        )

    def _handle_flights_by_airline(self, airline_name: str | None, language: str = "en") -> dict:
        if not airline_name:
            return self._handle_unknown("", language)

        total_count = self.flight_queries.count_flights_by_airline_name(airline_name)
        records = self.flight_queries.get_flights_by_airline_name(
            airline_name=airline_name,
            limit=15,
        )

        title_name = airline_name.title()

        return self.response_builder.build(
            response_type=COPILOT_RESPONSE_TYPES["DATA_BASED"],
            intent="FLIGHTS_BY_AIRLINE",
            title=f"Flights for {title_name}",
            message=f"I found {total_count} flights linked to an airline matching '{title_name}'.",
            metrics={"total_flights": total_count},
            records=records,
            recommended_module="Airlines",
            recommended_url="/airlines/",
            confidence=COPILOT_CONFIDENCE["HIGH"],
            source_note="This response is based on airline name filtering.",
        )

    def _handle_database_dictionary(self, language: str = "en") -> dict:
        snapshot = self.system_snapshot_service.build_snapshot()
        flight_summary = snapshot["flight_summary"]
        sync_summary = snapshot["api_sync_status"]

        records = [
            {
                "flight_number": "Flight",
                "route": "apps.flights.models.Flight",
                "status_label": "Core operational table",
                "source_type_label": "Database",
                "message": "Stores flight number, airline, route airports, status, schedule, live position and source type.",
            },
            {
                "flight_number": "Airline",
                "route": "apps.airlines.models.Airline",
                "status_label": "Reference table",
                "source_type_label": "Database",
                "message": "Stores carrier identity used by flight records and analytics.",
            },
            {
                "flight_number": "Airport",
                "route": "apps.airports.models.Airport",
                "status_label": "Reference table",
                "source_type_label": "Database",
                "message": "Stores airport codes, city, country and coordinates used for routes and map display.",
            },
            {
                "flight_number": "ApiSyncLog",
                "route": "apps.integrations.models.ApiSyncLog",
                "status_label": "Integration log",
                "source_type_label": "Database",
                "message": "Stores provider synchronization history, status, records received, created and updated.",
            },
        ]

        return self.response_builder.build(
            response_type=COPILOT_RESPONSE_TYPES["EXPLANATORY"],
            intent="DATABASE_DICTIONARY",
            title=self.language_service.text("database_title", language),
            message=self.language_service.text("database_message", language),
            bullets=[
                f"Current flight records: {flight_summary.get('total_flights', 0)}.",
                f"API flight records: {flight_summary.get('api_flights', 0)}.",
                f"Local flight records: {flight_summary.get('local_flights', 0)}.",
                f"Stored sync logs: {sync_summary.get('total_logs', 0)}.",
            ],
            metrics={
                "total_flights": flight_summary.get("total_flights", 0),
                "api_flights": flight_summary.get("api_flights", 0),
                "local_flights": flight_summary.get("local_flights", 0),
                "total_logs": sync_summary.get("total_logs", 0),
            },
            records=records,
            recommended_module="Operational Intelligence",
            recommended_url="/analytics/",
            confidence=COPILOT_CONFIDENCE["HIGH"],
            source_note="This response describes the project database at business level.",
        )

    def _handle_unknown(self, original_message: str, language: str = "en") -> dict:
        return self.response_builder.build_out_of_scope(
            intent=COPILOT_INTENTS["UNKNOWN"],
            title=self.language_service.text("unknown_title", language),
            message=self.language_service.text("unknown_message", language),
            suggested_prompts=[
                "Give me the current operational summary.",
                "Show flights needing attention.",
                "What is the API sync status?",
                "Show delayed flights.",
                "What is the busiest route?",
                "Explain the database structure.",
            ],
        )

    def _detect_forced_multilingual_intent(self, message: str) -> str | None:
        value = (message or "").lower().strip()

        if not value:
            return None

        operational_summary_patterns = [
            "сводка активных операций",
            "сводка операций",
            "сводка",
            "текущая ситуация",
            "текущая операционная ситуация",
            "операционная ситуация",
            "активные операции",
            "активных операций",
            "обзор операций",
            "состояние системы",
            "текущее состояние",
            "что происходит",
            "что сейчас",
            "résumé opérationnel",
            "resume operationnel",
            "situation opérationnelle",
            "situation operationnelle",
            "état opérationnel",
            "etat operationnel",
            "current operational summary",
            "operational summary",
            "current situation",
            "operational situation",
            "system state",
        ]

        if any(pattern in value for pattern in operational_summary_patterns):
            return COPILOT_INTENTS["OPERATIONAL_SUMMARY"]

        sync_patterns = [
            "статус синхронизации",
            "синхронизация api",
            "api синхронизация",
            "последняя синхронизация",
            "ошибки синхронизации",
            "sync status",
            "api sync status",
            "latest sync",
            "last sync",
            "statut de synchronisation",
            "synchronisation api",
        ]

        if any(pattern in value for pattern in sync_patterns):
            return COPILOT_INTENTS["API_SYNC_STATUS"]

        delayed_patterns = [
            "задержанные рейсы",
            "задержанные",
            "задержка рейсов",
            "рейсы с задержкой",
            "vols retardés",
            "vols retardes",
            "vols en retard",
            "delayed flights",
        ]

        if any(pattern in value for pattern in delayed_patterns):
            return COPILOT_INTENTS["DELAYED_FLIGHTS"]

        cancelled_patterns = [
            "отмененные рейсы",
            "отменённые рейсы",
            "отмененные",
            "отменённые",
            "отмена рейсов",
            "vols annulés",
            "vols annules",
            "cancelled flights",
            "canceled flights",
        ]

        if any(pattern in value for pattern in cancelled_patterns):
            return COPILOT_INTENTS["CANCELLED_FLIGHTS"]

        priority_patterns = [
            "требует внимания",
            "требуют внимания",
            "приоритетные рейсы",
            "приоритетные",
            "что требует внимания",
            "рейсы для проверки",
            "vols prioritaires",
            "vols à vérifier",
            "vols a verifier",
            "flights needing attention",
            "which flights need attention",
            "priority flights",
        ]

        if any(pattern in value for pattern in priority_patterns):
            return COPILOT_INTENTS["PRIORITY_FLIGHTS"]

        critical_patterns = [
            "критические рейсы",
            "критические",
            "критическая ситуация",
            "проблемные рейсы",
            "critical flights",
            "critical attention",
            "vols critiques",
        ]

        if any(pattern in value for pattern in critical_patterns):
            return COPILOT_INTENTS["CRITICAL_ATTENTION"]

        source_patterns = [
            "источники данных",
            "источник данных",
            "api и local",
            "api и локальные",
            "source breakdown",
            "data sources",
            "sources de données",
            "sources de donnees",
        ]

        if any(pattern in value for pattern in source_patterns):
            return COPILOT_INTENTS["SOURCE_BREAKDOWN"]

        database_patterns = [
            "база данных",
            "структура базы",
            "структура базы данных",
            "таблицы базы",
            "модели базы",
            "database",
            "database structure",
            "base de données",
            "base de donnees",
            "dictionnaire de la base",
        ]

        if any(pattern in value for pattern in database_patterns):
            return "DATABASE_DICTIONARY"

        return None

    def _is_database_dictionary_query(self, normalized_message: str) -> bool:
        value = normalized_message or ""

        patterns = [
            "database",
            "base de donne",
            "base de données",
            "dictionnaire",
            "dictionary",
            "schema",
            "structure",
            "tables",
            "models",
            "modeles",
            "модель",
            "модели",
            "таблица",
            "таблицы",
            "база данных",
            "структура базы",
        ]

        return any(pattern in value for pattern in patterns)