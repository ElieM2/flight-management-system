import os

COPILOT_RESPONSE_TYPES = {
    "DATA_BASED": "data_based",
    "EXPLANATORY": "explanatory",
    "UNAVAILABLE": "unavailable",
    "OUT_OF_SCOPE": "out_of_scope",
    "SYSTEM": "system",
}

COPILOT_CONFIDENCE = {
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
}

COPILOT_INTENTS = {
    "OPERATIONAL_SUMMARY": "operational_summary",
    "DELAYED_FLIGHTS": "delayed_flights",
    "CANCELLED_FLIGHTS": "cancelled_flights",
    "PRIORITY_FLIGHTS": "priority_flights",
    "API_SYNC_STATUS": "api_sync_status",
    "EXPLAIN_METRIC": "explain_metric",
    "MODULE_ROUTING": "module_routing",
    "SOURCE_BREAKDOWN": "source_breakdown",
    "CRITICAL_ATTENTION": "critical_attention",
    "UNKNOWN": "unknown",
}

COPILOT_SUPPORTED_METRICS = {
    "cancellation_rate": {
        "label": "Cancellation Rate",
        "keywords": [
            "cancellation rate",
            "cancel rate",
            "cancelled rate",
            "canceled rate",
            "taux d annulation",
            "taux annulation",
            "annulation",
            "annulations",
        ],
    },
    "delay_rate": {
        "label": "Delay Rate",
        "keywords": [
            "delay rate",
            "delayed rate",
            "taux de retard",
            "taux retard",
            "retard",
            "retards",
            "delay",
            "delays",
        ],
    },
    "api_flights": {
        "label": "API Flights",
        "keywords": [
            "api flights",
            "external flights",
            "provider flights",
            "vols api",
            "api",
            "provider",
            "external source",
        ],
    },
    "local_flights": {
        "label": "Local Flights",
        "keywords": [
            "local flights",
            "manual flights",
            "internal flights",
            "vols locaux",
            "local",
            "manual",
            "internal source",
        ],
    },
}

COPILOT_SCOPE_MESSAGE = (
    "I can help with flight supervision, delayed and cancelled flights, priority records, "
    "route volume, airline and airport activity, source distribution, API synchronization "
    "status, KPI explanations, and navigation inside the platform. Try asking for an "
    "operational summary, delayed flights, API sync status, or the busiest route."
)

COPILOT_QUICK_PROMPTS = [
    "Give me the current operational summary.",
    "Which flights need attention?",
    "Show me delayed flights.",
    "Show me cancelled flights.",
    "What is the API sync status?",
    "What is the top route by flight volume?",
    "Which airline has the most flights?",
    "Explain the cancellation rate.",
    "Which module should I open now?",
]

COPILOT_AI_SETTINGS = {
    "ENABLED": os.getenv("COPILOT_GPT4ALL_ENABLED", "False").lower() == "true",
    "TIMEOUT_SECONDS": 20,
    "MAX_MESSAGE_CHARS": 900,
    "MAX_RECORDS_FOR_REWRITE": 0,
    "MAX_METRICS_FOR_REWRITE": 0,
    "GPT4ALL_MODEL_NAME": os.getenv(
        "COPILOT_GPT4ALL_MODEL_NAME",
        "Meta-Llama-3-8B-Instruct.Q4_0.gguf",
    ),
    "GPT4ALL_MODEL_PATH": os.getenv(
        "COPILOT_GPT4ALL_MODEL_PATH",
        os.path.join(os.getenv("LOCALAPPDATA", ""), "nomic.ai", "GPT4All"),
    ),
    "GPT4ALL_DEVICE": os.getenv("COPILOT_GPT4ALL_DEVICE", "cpu"),
    "GPT4ALL_THREADS": int(os.getenv("COPILOT_GPT4ALL_THREADS", "8")),
    "GPT4ALL_CTX": int(os.getenv("COPILOT_GPT4ALL_CTX", "2048")),
    "GPT4ALL_MAX_TOKENS": int(os.getenv("COPILOT_GPT4ALL_MAX_TOKENS", "160")),
    "GPT4ALL_TEMP": float(os.getenv("COPILOT_GPT4ALL_TEMP", "0.1")),
}

COPILOT_AI_ALLOWED_RESPONSE_TYPES = {
    "explanatory",
}

COPILOT_AI_SYSTEM_RULES = [
    "You are a controlled rewriting layer for an airline operations platform.",
    "Rewrite only the main message.",
    "Never invent facts.",
    "Never change numbers.",
    "Never add new operational data.",
    "Never add urgency, causes, advice, recommendations, interpretations, or conclusions.",
    "Never rewrite metrics.",
    "Never rewrite records.",
    "Never rewrite module recommendations or URLs.",
    "Keep the meaning exactly the same.",
    "Keep the output concise and professional.",
    "Return only the rewritten message text.",
]