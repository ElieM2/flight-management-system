from django.core.management.base import BaseCommand

from apps.copilot.services.external_llm_client import ExternalLLMClient


class Command(BaseCommand):
    help = "Test the external LLM connection for Operational Copilot."

    def handle(self, *args, **options):
        client = ExternalLLMClient()

        self.stdout.write("Testing external LLM connection...")
        self.stdout.write(f"Provider: {client.provider}")
        self.stdout.write(f"Model: {client.model}")
        self.stdout.write(f"Available: {client.is_available()}")

        result = client.generate_text(
            system_prompt=(
                "You are LogosFlight Operational Copilot. "
                "Answer briefly. Do not invent data."
            ),
            user_prompt=(
                "Reply in French with one short sentence: "
                "the external AI connection is working."
            ),
            max_output_tokens=120,
        )

        if not result.ok:
            self.stdout.write(self.style.ERROR("External LLM test failed."))
            self.stdout.write(self.style.ERROR(result.error or "Unknown error."))
            return

        self.stdout.write(self.style.SUCCESS("External LLM test succeeded."))
        self.stdout.write("")
        self.stdout.write(result.text)