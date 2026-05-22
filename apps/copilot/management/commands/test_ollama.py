from django.core.management.base import BaseCommand

from apps.copilot.services.ollama_client import OllamaClient


class Command(BaseCommand):
    help = "Test the local Ollama connection for Operational Copilot."

    def handle(self, *args, **options):
        client = OllamaClient()

        self.stdout.write("Testing Ollama connection...")
        self.stdout.write(f"Enabled: {client.enabled}")
        self.stdout.write(f"Provider: {client.provider}")
        self.stdout.write(f"Base URL: {client.base_url}")
        self.stdout.write(f"Model: {client.model}")
        self.stdout.write(f"Available: {client.is_available()}")

        result = client.generate_text(
            system_prompt=(
                "You are LogosFlight Operational Copilot. "
                "Answer briefly. Do not invent operational data."
            ),
            user_prompt=(
                "Réponds en français en une seule phrase : "
                "la connexion IA locale fonctionne."
            ),
        )

        if not result.ok:
            self.stdout.write(self.style.ERROR("Ollama test failed."))
            self.stdout.write(self.style.ERROR(result.error or "Unknown error."))
            return

        self.stdout.write(self.style.SUCCESS("Ollama test succeeded."))
        self.stdout.write("")
        self.stdout.write(result.text)