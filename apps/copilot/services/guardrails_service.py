import re

from apps.copilot.constants import (
    COPILOT_AI_ALLOWED_RESPONSE_TYPES,
    COPILOT_AI_SETTINGS,
)


class GuardrailsService:
    """
    Validates optional local message refinement before it is returned
    to the frontend interface.
    """

    def should_attempt_rewrite(self, business_response: dict) -> bool:
        if not business_response:
            return False

        if not COPILOT_AI_SETTINGS["ENABLED"]:
            return False

        response_type = business_response.get("type")

        if response_type not in COPILOT_AI_ALLOWED_RESPONSE_TYPES:
            return False

        message = (business_response.get("message") or "").strip()

        if not message:
            return False

        return True

    def sanitize_rewrite_result(
        self,
        rewrite_result: dict | None,
        business_response: dict,
    ) -> dict | None:
        if not rewrite_result:
            return None

        rewritten_message = (rewrite_result.get("rewritten_message") or "").strip()
        original_message = (business_response.get("message") or "").strip()

        if not rewritten_message or not original_message:
            return None

        rewritten_message = rewritten_message[:COPILOT_AI_SETTINGS["MAX_MESSAGE_CHARS"]]

        if self._looks_invalid(rewritten_message, original_message):
            return None

        return {
            "rewritten_message": rewritten_message,
        }

    def merge_rewrite_into_response(
        self,
        business_response: dict,
        rewrite_result: dict | None,
    ) -> dict:
        final_response = dict(business_response)

        final_response["rewritten_message"] = (
            None if not rewrite_result else rewrite_result["rewritten_message"]
        )

        return final_response

    def _looks_invalid(self, rewritten_message: str, original_message: str) -> bool:
        if self._extract_numbers(original_message) != self._extract_numbers(rewritten_message):
            return True

        blocked_phrases = [
            "immediate attention",
            "real-time tracking",
            "operational impacts",
            "root cause",
            "authority to address",
            "we recommend",
            "urgent",
            "critical escalation",
            "follow-up on impacts",
            "explanation:",
            "reasoning:",
            "do not add any information",
            '"data":',
            "{",
            "}",
        ]

        rewritten_lower = rewritten_message.lower()
        original_lower = original_message.lower()

        for phrase in blocked_phrases:
            if phrase in rewritten_lower and phrase not in original_lower:
                return True

        max_allowed_length = int(len(original_message) * 1.6)

        if len(rewritten_message) > max_allowed_length:
            return True

        return False

    def _extract_numbers(self, text: str) -> list[str]:
        return re.findall(r"\d+(?:\.\d+)?", text or "")