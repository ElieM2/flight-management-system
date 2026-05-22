from apps.copilot.constants import COPILOT_AI_SETTINGS, COPILOT_AI_SYSTEM_RULES


class PromptBuilder:
    """
    Builds compact prompts for optional local message refinement.

    This class is used only after the business response has already been
    prepared by the Django application.
    """

    def build_rewrite_prompt(self, business_response: dict) -> dict:
        message = (business_response.get("message") or "").strip()

        return {
            "task": "refine_message_only",
            "rules": COPILOT_AI_SYSTEM_RULES,
            "response_type": business_response.get("type"),
            "intent": business_response.get("intent"),
            "title": business_response.get("title"),
            "message": message[:COPILOT_AI_SETTINGS["MAX_MESSAGE_CHARS"]],
            "expected_output": {
                "rewritten_message": "string",
            },
        }

    def build_system_message(self) -> str:
        return (
            "You refine the wording of messages for a flight operations platform.\n"
            "Refine only the main message.\n"
            "Do not add facts.\n"
            "Do not change numbers.\n"
            "Do not add urgency, causes, advice, recommendations or interpretations.\n"
            "Do not rewrite records, metrics or module routing.\n"
            "Return only the final message text.\n"
            "If the original message is already clear, make only minimal changes."
        )

    def build_user_prompt(self, business_response: dict) -> str:
        message = (business_response.get("message") or "").strip()
        response_type = (business_response.get("type") or "").strip()
        intent = (business_response.get("intent") or "").strip()
        title = (business_response.get("title") or "").strip()

        return (
            f"Response type: {response_type}\n"
            f"Intent: {intent}\n"
            f"Title: {title}\n\n"
            f"Message:\n{message}\n\n"
            "Refine only the message above."
        )