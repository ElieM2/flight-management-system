from django.urls import path
from apps.copilot.views import CopilotAskView, copilot_panel_view

app_name = "copilot"

urlpatterns = [
    path("", copilot_panel_view, name="panel"),
    path("ask/", CopilotAskView.as_view(), name="ask"),
]