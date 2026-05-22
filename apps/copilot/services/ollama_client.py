from __future__ import annotations

from dataclasses import dataclass

import requests
from django.conf import settings


@dataclass
class OllamaResult:
    ok: bool
    text: str
    model: str
    error: str | None = None


class OllamaClient:
    """
    Local LLM client for Operational Copilot.

    This client talks to Ollama running locally on the computer.

    Important:
    - It does not read the database.
    - It must not invent flight data.
    - Django repositories remain the only trusted source for operational facts.
    - Ollama is used to make answers more natural and multilingual.
    """

    def __init__(self):
        self.enabled = getattr(settings, "COPILOT_LOCAL_LLM_ENABLED", False)
        self.provider = getattr(settings, "COPILOT_LOCAL_LLM_PROVIDER", "ollama")
        self.base_url = getattr(settings, "COPILOT_OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.model = getattr(settings, "COPILOT_OLLAMA_MODEL", "llama3.2:3b")
        self.temperature = getattr(settings, "COPILOT_OLLAMA_TEMPERATURE", 0.2)
        self.timeout = getattr(settings, "COPILOT_OLLAMA_TIMEOUT_SECONDS", 60)

    def is_available(self) -> bool:
        if not self.enabled:
            return False

        if self.provider != "ollama":
            return False

        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> OllamaResult:
        if not self.is_available():
            return OllamaResult(
                ok=False,
                text="",
                model=self.model,
                error="Ollama is disabled or not available.",
            )

        payload = {
            "model": self.model,
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()
            message = data.get("message", {})
            text = message.get("content", "")

            return OllamaResult(
                ok=True,
                text=(text or "").strip(),
                model=self.model,
                error=None,
            )

        except requests.RequestException as exc:
            return OllamaResult(
                ok=False,
                text="",
                model=self.model,
                error=f"{exc.__class__.__name__}: {exc}",
            )
        except ValueError as exc:
            return OllamaResult(
                ok=False,
                text="",
                model=self.model,
                error=f"Invalid JSON response from Ollama: {exc}",
            )