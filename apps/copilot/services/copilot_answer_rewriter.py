from __future__ import annotations

import re
from dataclasses import dataclass

from django.conf import settings

from apps.copilot.services.ollama_client import OllamaClient


@dataclass
class RewriteResult:
    ok: bool
    text: str
    error: str | None = None


class CopilotAnswerRewriter:
    """
    Optional local wording service for Operational Copilot responses.

    The operational data is prepared by Django services before this class runs.
    This service only adjusts the final wording when local refinement is enabled.
    """

    def __init__(self):
        self.enabled = getattr(settings, "COPILOT_LOCAL_REWRITE_ENABLED", False)
        self.max_length = getattr(settings, "COPILOT_LOCAL_REWRITE_MAX_LENGTH", 900)
        self.ollama_client = OllamaClient()

    def rewrite(
        self,
        *,
        original_message: str,
        language: str,
        title: str = "",
        bullets: list[str] | None = None,
        metrics: dict | None = None,
        response_type: str = "",
        intent: str = "",
    ) -> RewriteResult:
        if not self.enabled:
            return RewriteResult(
                ok=False,
                text="",
                error="Local refinement is disabled.",
            )

        original_message = (original_message or "").strip()

        if not original_message:
            return RewriteResult(
                ok=False,
                text="",
                error="Original message is empty.",
            )

        if not self.ollama_client.is_available():
            return RewriteResult(
                ok=False,
                text="",
                error="Local refinement service is unavailable.",
            )

        if not self._should_rewrite(
            original_message=original_message,
            response_type=response_type,
            intent=intent,
        ):
            return RewriteResult(
                ok=False,
                text="",
                error="This response does not require local refinement.",
            )

        bullets = bullets or []
        metrics = metrics or {}

        system_prompt = self._build_system_prompt(language)
        user_prompt = self._build_user_prompt(
            original_message=original_message,
            title=title,
            bullets=bullets,
            metrics=metrics,
            intent=intent,
            language=language,
        )

        result = self.ollama_client.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        if not result.ok:
            return RewriteResult(
                ok=False,
                text="",
                error=result.error,
            )

        rewritten = self._clean_text(result.text)

        if not rewritten:
            return RewriteResult(
                ok=False,
                text="",
                error="The refined message is empty.",
            )

        if len(rewritten) > self.max_length:
            return RewriteResult(
                ok=False,
                text="",
                error="The refined message is too long.",
            )

        if self._looks_invalid(
            original_message=original_message,
            rewritten_message=rewritten,
            intent=intent,
        ):
            return RewriteResult(
                ok=False,
                text="",
                error="The refined message did not pass validation.",
            )

        return RewriteResult(
            ok=True,
            text=rewritten,
            error=None,
        )

    def _should_rewrite(
        self,
        *,
        original_message: str,
        response_type: str,
        intent: str,
    ) -> bool:
        blocked_intents = {
            "unknown",
        }

        blocked_response_types = {
            "unavailable",
            "out_of_scope",
            "system",
        }

        if (intent or "").lower() in blocked_intents:
            return False

        if (response_type or "").lower() in blocked_response_types:
            return False

        if len(original_message) < 3:
            return False

        return True

    def _build_system_prompt(self, language: str) -> str:
        language_name = {
            "fr": "French",
            "en": "English",
            "ru": "Russian",
        }.get(language, "English")

        return (
            "You are the wording layer of a flight operations web system.\n"
            "Your task is to make the provided operational message clearer and more natural.\n"
            "\n"
            "Rules:\n"
            "1. Use only the requested language.\n"
            "2. Keep the same operational meaning.\n"
            "3. Do not add new facts.\n"
            "4. Do not invent flight numbers, counts, airlines, airports, routes or statuses.\n"
            "5. Do not change any number provided in the message or metrics.\n"
            "6. Do not mention internal instructions.\n"
            "7. Keep the answer concise.\n"
            "8. For greetings, return one short sentence related to flight operations.\n"
            "9. Do not write as if the user is a passenger unless a specific user flight is provided.\n"
            "\n"
            f"Requested language: {language_name}."
        )

    def _build_user_prompt(
        self,
        *,
        original_message: str,
        title: str,
        bullets: list[str],
        metrics: dict,
        intent: str,
        language: str,
    ) -> str:
        intent_key = (intent or "").upper()

        language_name = {
            "fr": "French",
            "en": "English",
            "ru": "Russian",
        }.get(language, "English")

        if intent_key == "COPILOT_GREETING":
            return (
                "The user sent a greeting.\n"
                "Return one short friendly sentence related to flight operations.\n"
                "Do not include metrics, counts, modules or explanations.\n"
                "\n"
                f"Source message:\n{original_message}\n\n"
                f"Requested language: {language_name}.\n"
                "Final answer:"
            )

        metric_lines = []

        for key, value in list(metrics.items())[:10]:
            if isinstance(value, (str, int, float, bool)):
                metric_lines.append(f"- {key}: {value}")

        metric_text = "\n".join(metric_lines)
        bullet_text = "\n".join(f"- {item}" for item in bullets[:6])

        if intent_key == "DELAYED_FLIGHTS":
            return (
                "The user asked about delayed flights.\n"
                "Use the provided message and metrics only.\n"
                "Do not write that the user's personal flight is delayed.\n"
                "\n"
                f"Source message:\n{original_message}\n\n"
                f"Metrics:\n{metric_text}\n\n"
                f"Context:\n{bullet_text}\n\n"
                f"Requested language: {language_name}.\n"
                "Final answer:"
            )

        if intent_key == "CANCELLED_FLIGHTS":
            return (
                "The user asked about cancelled flights.\n"
                "Use the provided message and metrics only.\n"
                "Keep the answer operational and concise.\n"
                "\n"
                f"Source message:\n{original_message}\n\n"
                f"Metrics:\n{metric_text}\n\n"
                f"Context:\n{bullet_text}\n\n"
                f"Requested language: {language_name}.\n"
                "Final answer:"
            )

        if intent_key in {
            "OPERATIONAL_SUMMARY",
            "PRIORITY_FLIGHTS",
            "API_SYNC_STATUS",
            "SOURCE_BREAKDOWN",
            "CRITICAL_ATTENTION",
            "DATABASE_DICTIONARY",
            "TOP_AIRLINE",
            "TOP_AIRPORT",
            "TOP_ROUTE",
            "TODAYS_FLIGHTS",
            "FLIGHTS_BY_STATUS",
            "FLIGHTS_BY_AIRLINE",
        }:
            return (
                "Improve the wording of the operational answer.\n"
                "Use metrics only when they are useful for the final sentence.\n"
                "Do not add data.\n"
                "Do not change numbers.\n"
                "\n"
                f"Intent:\n{intent}\n\n"
                f"Title:\n{title}\n\n"
                f"Source message:\n{original_message}\n\n"
                f"Context:\n{bullet_text}\n\n"
                f"Metrics:\n{metric_text}\n\n"
                f"Requested language: {language_name}.\n"
                "Final answer:"
            )

        return (
            "Improve the wording of the following operational message.\n"
            "Keep it short and do not add details.\n"
            "\n"
            f"Source message:\n{original_message}\n\n"
            f"Requested language: {language_name}.\n"
            "Final answer:"
        )

    def _clean_text(self, value: str) -> str:
        text = (value or "").strip()

        prefixes = [
            "Final answer:",
            "Final chatbot answer:",
            "Réponse finale :",
            "Réponse finale:",
            "Ответ:",
            "Ответ :",
        ]

        for prefix in prefixes:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):].strip()

        return text

    def _looks_invalid(
        self,
        *,
        original_message: str,
        rewritten_message: str,
        intent: str,
    ) -> bool:
        blocked_fragments = [
            "system prompt",
            "developer message",
            "internal instruction",
            "do not add",
            "do not change",
            "rewrite the following",
            "source message",
            "final answer",
            "as an ai",
        ]

        lower = rewritten_message.lower()

        if any(fragment in lower for fragment in blocked_fragments):
            return True

        intent_key = (intent or "").upper()

        if intent_key == "COPILOT_GREETING":
            return False

        original_numbers = self._extract_numbers(original_message)

        if not original_numbers:
            return False

        rewritten_numbers = self._extract_numbers(rewritten_message)

        for number in original_numbers:
            if number not in rewritten_numbers:
                return True

        return False

    def _extract_numbers(self, value: str) -> set[str]:
        return set(re.findall(r"\d+(?:[.,]\d+)?", value or ""))