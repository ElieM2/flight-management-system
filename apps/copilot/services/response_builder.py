from apps.copilot.constants import COPILOT_CONFIDENCE, COPILOT_RESPONSE_TYPES


class ResponseBuilder:
    """
    Builds the standard response payload used by the Operational Copilot interface.

    The frontend depends on a stable JSON structure. Existing keys should be kept
    even when some sections are empty.
    """

    def build(
        self,
        *,
        response_type: str,
        intent: str,
        title: str,
        message: str,
        bullets: list[str] | None = None,
        metrics: dict | None = None,
        records: list[dict] | None = None,
        recommended_module: str | None = None,
        recommended_url: str | None = None,
        confidence: str | None = None,
        source_note: str | None = None,
        rewritten_message: str | None = None,
        suggested_prompts: list[str] | None = None,
    ) -> dict:
        return {
            "type": response_type,
            "intent": intent,
            "title": (title or "").strip(),
            "message": (message or "").strip(),
            "bullets": bullets or [],
            "metrics": metrics or {},
            "records": records or [],
            "recommended_module": recommended_module,
            "recommended_url": recommended_url,
            "confidence": confidence or COPILOT_CONFIDENCE["HIGH"],
            "source_note": source_note or "",
            "rewritten_message": rewritten_message,
            "suggested_prompts": suggested_prompts or [],
        }

    def build_system_message(self, *, intent: str, title: str, message: str) -> dict:
        return self.build(
            response_type=COPILOT_RESPONSE_TYPES["SYSTEM"],
            intent=intent,
            title=title,
            message=message,
            confidence=COPILOT_CONFIDENCE["HIGH"],
            source_note="This response is based on the internal application logic.",
        )

    def build_unavailable(self, *, intent: str, title: str, message: str) -> dict:
        return self.build(
            response_type=COPILOT_RESPONSE_TYPES["UNAVAILABLE"],
            intent=intent,
            title=title,
            message=message,
            confidence=COPILOT_CONFIDENCE["LOW"],
            source_note="The requested information is not currently available in the system data.",
        )

    def build_out_of_scope(
        self,
        *,
        intent: str,
        title: str,
        message: str,
        suggested_prompts: list[str] | None = None,
    ) -> dict:
        return self.build(
            response_type=COPILOT_RESPONSE_TYPES["OUT_OF_SCOPE"],
            intent=intent,
            title=title,
            message=message,
            bullets=[
                "Supported requests include flights, statuses, delays, cancellations, routes, airlines, airports, data sources and API synchronization.",
                "The answer is based on internal project data and predefined business rules.",
                "Try a more specific operational question to receive a database-based answer.",
            ],
            confidence=COPILOT_CONFIDENCE["MEDIUM"],
            source_note="The request was not matched to a supported operational intent.",
            suggested_prompts=suggested_prompts or [
                "Give me the current operational summary.",
                "Which flights need attention?",
                "What is the API sync status?",
                "Show delayed flights.",
                "What is the busiest route?",
            ],
        )