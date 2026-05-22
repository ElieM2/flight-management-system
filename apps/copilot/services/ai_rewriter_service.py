from __future__ import annotations

import json
import logging
import re
import threading

from apps.copilot.constants import COPILOT_AI_SETTINGS
from apps.copilot.services.prompt_builder import PromptBuilder

try:
    from gpt4all import GPT4All
except Exception:  # pragma: no cover
    GPT4All = None


logger = logging.getLogger(__name__)


class AIRewriterService:
    """
    Optional local text refinement service for Copilot responses.

    The business data is prepared before this service is called. This class only
    improves the final wording when a local model is available.
    """

    _model_instance = None
    _model_lock = threading.Lock()

    def __init__(self):
        self.prompt_builder = PromptBuilder()

    def rewrite(self, business_response: dict) -> dict | None:
        if GPT4All is None:
            logger.debug("Local text refinement is unavailable.")
            return None

        model = self._get_model()

        if model is None:
            logger.debug("Local text refinement model is not loaded.")
            return None

        system_message = self.prompt_builder.build_system_message()
        user_prompt = self.prompt_builder.build_user_prompt(business_response)
        request_payload = f"{system_message}\n\n{user_prompt}"

        try:
            rewritten = model.generate(
                request_payload,
                max_tokens=COPILOT_AI_SETTINGS["GPT4ALL_MAX_TOKENS"],
                temp=COPILOT_AI_SETTINGS["GPT4ALL_TEMP"],
                top_k=20,
                top_p=0.3,
                repeat_penalty=1.1,
                repeat_last_n=32,
                n_batch=4,
                streaming=False,
            )
        except Exception as exc:
            logger.debug("Local text refinement failed: %s", exc.__class__.__name__)
            return None

        rewritten_text = (rewritten or "").strip()

        if not rewritten_text:
            return None

        normalized = self._normalize_output(rewritten_text)

        if not normalized:
            return None

        return {
            "rewritten_message": normalized,
        }

    def _get_model(self):
        if self.__class__._model_instance is not None:
            return self.__class__._model_instance

        with self.__class__._model_lock:
            if self.__class__._model_instance is not None:
                return self.__class__._model_instance

            model_name = COPILOT_AI_SETTINGS["GPT4ALL_MODEL_NAME"]
            model_path = COPILOT_AI_SETTINGS["GPT4ALL_MODEL_PATH"] or None
            device = COPILOT_AI_SETTINGS["GPT4ALL_DEVICE"]
            n_threads = COPILOT_AI_SETTINGS["GPT4ALL_THREADS"]
            n_ctx = COPILOT_AI_SETTINGS["GPT4ALL_CTX"]

            try:
                self.__class__._model_instance = GPT4All(
                    model_name=model_name,
                    model_path=model_path,
                    allow_download=False,
                    n_threads=n_threads,
                    device=device,
                    n_ctx=n_ctx,
                    ngl=0,
                    verbose=False,
                )
            except Exception as exc:
                logger.debug("Local model loading failed: %s", exc.__class__.__name__)
                self.__class__._model_instance = None

        return self.__class__._model_instance

    def _normalize_output(self, text: str) -> str:
        cleaned = text.strip()

        cleaned = (
            cleaned
            .replace("```json", "")
            .replace("```python", "")
            .replace("```", "")
            .strip()
        )

        json_candidate = self._extract_json_object(cleaned)

        if json_candidate:
            try:
                parsed = json.loads(json_candidate)

                if isinstance(parsed, dict):
                    data_value = parsed.get("data")

                    if isinstance(data_value, str) and data_value.strip():
                        return data_value.strip()
            except Exception:
                pass

        noisy_prefixes = [
            "Response:",
            "Rewritten response:",
            "Rewritten message:",
            "Here is a rewritten version of the response:",
            "Do not add any information.",
        ]

        for prefix in noisy_prefixes:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()

        explanation_markers = [
            "\nExplanation:",
            "Explanation:",
            "\nReasoning:",
            "Reasoning:",
        ]

        for marker in explanation_markers:
            if marker in cleaned:
                cleaned = cleaned.split(marker, 1)[0].strip()

        match = re.search(r'"data"\s*:\s*"([^"]+)"', cleaned, flags=re.DOTALL)

        if match:
            return match.group(1).strip()

        sentence_candidates = re.split(r"(?<=[.!?])\s+", cleaned)
        sentence_candidates = [
            sentence.strip()
            for sentence in sentence_candidates
            if sentence.strip()
        ]

        if sentence_candidates:
            return " ".join(sentence_candidates[:2]).strip()

        return cleaned.strip()

    def _extract_json_object(self, text: str) -> str | None:
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1 or end <= start:
            return None

        return text[start:end + 1]