from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings


@dataclass
class ExternalLLMResult:
    ok: bool
    text: str
    provider: str
    model: str
    error: str | None = None


class ExternalLLMClient:
    """
    Optional external text service client.

    The main Copilot module does not depend on this client for operational
    calculations. Flight data, statistics and business facts must always come
    from Django repositories and project services.
    """

    def __init__(self):
        self.enabled = getattr(settings, "COPILOT_EXTERNAL_SERVICE_ENABLED", False)
        self.provider = getattr(settings, "COPILOT_EXTERNAL_SERVICE_PROVIDER", "disabled")
        self.model = getattr(settings, "COPILOT_EXTERNAL_SERVICE_MODEL", "local")
        self.temperature = getattr(settings, "COPILOT_EXTERNAL_SERVICE_TEMPERATURE", 0.2)

    def is_available(self) -> bool:
        return False

    def generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int = 700,
    ) -> ExternalLLMResult:
        return ExternalLLMResult(
            ok=False,
            text="",
            provider=self.provider,
            model=self.model,
            error="External text service is not enabled for this project.",
        )