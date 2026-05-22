import json

from django.http import JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.copilot.services.copilot_service import CopilotService


def copilot_panel_view(request):
    return render(request, "copilot/copilot_panel.html")


@method_decorator(csrf_exempt, name="dispatch")
class CopilotAskView(View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        try:
            payload = self._parse_json_body(request)
        except ValueError:
            return JsonResponse(
                {
                    "ok": False,
                    "error": "Invalid JSON body.",
                },
                status=400,
            )

        message = (payload.get("message") or "").strip()
        interface_language = self._normalize_language(payload.get("language"))

        if not message:
            return JsonResponse(
                {
                    "ok": False,
                    "error": "The 'message' field is required.",
                },
                status=400,
            )

        service = CopilotService()
        response_payload = service.handle_message(
            message=message,
            interface_language=interface_language,
        )

        return JsonResponse(
            {
                "ok": True,
                "data": response_payload,
            },
            status=200,
        )

    def _parse_json_body(self, request) -> dict:
        if not request.body:
            return {}

        try:
            return json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ValueError("Invalid JSON")

    def _normalize_language(self, value: str | None) -> str | None:
        language = (value or "").strip().lower()

        if language.startswith("fr"):
            return "fr"

        if language.startswith("ru"):
            return "ru"

        if language.startswith("en"):
            return "en"

        return None