import re
import unicodedata

from apps.copilot.constants import COPILOT_INTENTS, COPILOT_SUPPORTED_METRICS


class IntentDetector:
    """
    Rule-based intent detector for operational flight questions.

    It normalizes English, French and Russian input and maps supported questions
    to stable business intents used by the Copilot service.
    """

    STATUS_ALIASES = {
        "scheduled": [
            "scheduled",
            "programmed",
            "planned",
            "programme",
            "programmé",
            "programmés",
            "planifie",
            "planifié",
            "planifiés",
            "запланирован",
            "запланированные",
            "по расписанию",
            "расписание",
        ],
        "boarding": [
            "boarding",
            "embarquement",
            "посадка",
            "на посадке",
        ],
        "departed": [
            "departed",
            "departure",
            "depart",
            "départ",
            "parti",
            "partis",
            "вылетел",
            "вылетели",
            "отправлен",
            "отправленные",
        ],
        "in_air": [
            "in air",
            "in_air",
            "airborne",
            "en vol",
            "dans les airs",
            "в полете",
            "в полёте",
            "летит",
            "летят",
        ],
        "landed": [
            "landed",
            "arrived",
            "arrival",
            "atterri",
            "atterris",
            "arrivé",
            "arrivés",
            "приземлился",
            "приземлились",
            "прибыл",
            "прибыли",
        ],
        "delayed": [
            "delayed",
            "delay",
            "delays",
            "retard",
            "retards",
            "retardé",
            "retardés",
            "задержан",
            "задержанные",
            "задержка",
            "задержки",
        ],
        "cancelled": [
            "cancelled",
            "canceled",
            "cancel",
            "cancellation",
            "annulé",
            "annulés",
            "annulation",
            "отменен",
            "отменён",
            "отмененные",
            "отменённые",
            "отмена",
            "отмены",
        ],
    }

    def detect(self, message: str) -> dict:
        raw_message = (message or "").strip()
        normalized = self._normalize(raw_message)

        if not normalized:
            return self._result(
                intent=COPILOT_INTENTS["UNKNOWN"],
                normalized_message=normalized,
            )

        metric_key = self._detect_metric(normalized)

        if self._is_greeting(normalized):
            return self._result(
                intent="COPILOT_GREETING",
                normalized_message=normalized,
                metric_key=metric_key,
            )

        if self._is_database_dictionary_query(normalized):
            return self._result(
                intent="DATABASE_DICTIONARY",
                normalized_message=normalized,
                metric_key=metric_key,
            )

        if self._is_operational_summary_query(normalized):
            return self._result(
                intent=COPILOT_INTENTS["OPERATIONAL_SUMMARY"],
                normalized_message=normalized,
                metric_key=metric_key,
            )

        if self._is_sync_query(normalized):
            return self._result(
                intent=COPILOT_INTENTS["API_SYNC_STATUS"],
                normalized_message=normalized,
                metric_key=metric_key,
            )

        if self._is_priority_query(normalized):
            return self._result(
                intent=COPILOT_INTENTS["PRIORITY_FLIGHTS"],
                normalized_message=normalized,
                metric_key=metric_key,
            )

        if self._is_critical_query(normalized):
            return self._result(
                intent=COPILOT_INTENTS["CRITICAL_ATTENTION"],
                normalized_message=normalized,
                metric_key=metric_key,
            )

        if self._is_source_breakdown_query(normalized):
            return self._result(
                intent=COPILOT_INTENTS["SOURCE_BREAKDOWN"],
                normalized_message=normalized,
                metric_key=metric_key,
            )

        if self._is_module_routing_query(normalized):
            return self._result(
                intent=COPILOT_INTENTS["MODULE_ROUTING"],
                normalized_message=normalized,
                metric_key=metric_key,
            )

        if self._is_top_airline_query(normalized):
            return self._result(
                intent="TOP_AIRLINE",
                normalized_message=normalized,
                metric_key=metric_key,
            )

        if self._is_top_airport_query(normalized):
            return self._result(
                intent="TOP_AIRPORT",
                normalized_message=normalized,
                metric_key=metric_key,
            )

        if self._is_top_route_query(normalized):
            return self._result(
                intent="TOP_ROUTE",
                normalized_message=normalized,
                metric_key=metric_key,
            )

        if self._is_today_flights_query(normalized):
            return self._result(
                intent="TODAYS_FLIGHTS",
                normalized_message=normalized,
                metric_key=metric_key,
            )

        status = self._extract_status(normalized)

        if status == "delayed":
            return self._result(
                intent=COPILOT_INTENTS["DELAYED_FLIGHTS"],
                normalized_message=normalized,
                metric_key=metric_key,
                extracted_value=status,
            )

        if status == "cancelled":
            return self._result(
                intent=COPILOT_INTENTS["CANCELLED_FLIGHTS"],
                normalized_message=normalized,
                metric_key=metric_key,
                extracted_value=status,
            )

        if status:
            return self._result(
                intent="FLIGHTS_BY_STATUS",
                normalized_message=normalized,
                metric_key=metric_key,
                extracted_value=status,
            )

        airline_name = self._extract_airline_name(normalized)

        if airline_name:
            return self._result(
                intent="FLIGHTS_BY_AIRLINE",
                normalized_message=normalized,
                metric_key=metric_key,
                extracted_value=airline_name,
            )

        if self._is_metric_explanation_query(normalized, metric_key):
            return self._result(
                intent=COPILOT_INTENTS["EXPLAIN_METRIC"],
                normalized_message=normalized,
                metric_key=metric_key,
            )

        if self._looks_like_operational_question(normalized):
            return self._result(
                intent=COPILOT_INTENTS["OPERATIONAL_SUMMARY"],
                normalized_message=normalized,
                metric_key=metric_key,
            )

        return self._result(
            intent=COPILOT_INTENTS["UNKNOWN"],
            normalized_message=normalized,
            metric_key=metric_key,
        )

    def _result(
        self,
        *,
        intent: str,
        normalized_message: str,
        metric_key: str | None = None,
        extracted_value: str | None = None,
    ) -> dict:
        return {
            "intent": intent,
            "metric_key": metric_key,
            "normalized_message": normalized_message,
            "extracted_value": extracted_value,
        }

    def _normalize(self, message: str) -> str:
        value = self._remove_accents(message.lower().strip())

        replacements = {
            "aujourd hui": "today",
            "aujourdhui": "today",
            "maintenant": "now",
            "actuel": "current",
            "actuelle": "current",
            "etat": "state",
            "état": "state",
            "situation actuelle": "current situation",
            "situation operationnelle": "operational situation",
            "opérationnelle": "operational",
            "resume": "summary",
            "résumé": "summary",
            "bilan": "summary",
            "donne moi": "show me",
            "montre moi": "show me",
            "affiche moi": "show me",
            "combien": "how many",
            "vols": "flights",
            "vol": "flight",
            "compagnie": "airline",
            "compagnies": "airlines",
            "aeroport": "airport",
            "aéroport": "airport",
            "aeroports": "airports",
            "aéroports": "airports",
            "retard": "delayed",
            "retards": "delayed",
            "retarde": "delayed",
            "retardé": "delayed",
            "annule": "cancelled",
            "annulé": "cancelled",
            "annules": "cancelled",
            "annulés": "cancelled",
            "annulation": "cancelled",
            "synchronisation": "sync",
            "synchroniser": "sync",
            "prioritaire": "priority",
            "prioritaires": "priority",
            "critique": "critical",
            "critiques": "critical",

            "сводка активных операций": "summary active operations",
            "сводка операций": "summary operations",
            "сводка": "summary",
            "сводку": "summary",
            "обзор": "overview",
            "резюме": "summary",
            "итог": "summary",
            "текущая ситуация": "current situation",
            "текущая операционная ситуация": "current operational situation",
            "операционная ситуация": "operational situation",
            "текущее состояние": "current state",
            "состояние системы": "system state",
            "активные операции": "active operations",
            "активных операций": "active operations",
            "что происходит": "what is happening",
            "что сейчас": "what now",

            "покажи": "show me",
            "показать": "show",
            "дай": "show me",
            "сколько": "how many",
            "какие": "which",
            "какой": "which",
            "какая": "which",
            "где": "where",
            "что": "what",

            "рейсы": "flights",
            "рейсов": "flights",
            "рейс": "flight",
            "авиакомпании": "airlines",
            "авиакомпания": "airline",
            "аэропорты": "airports",
            "аэропорт": "airport",
            "маршруты": "routes",
            "маршрут": "route",
            "источники": "sources",
            "источник": "source",
            "синхронизация": "sync",
            "синхронизации": "sync",
            "статус синхронизации": "sync status",
            "последняя синхронизация": "latest sync",
            "api синхронизация": "api sync",
            "ошибки синхронизации": "sync failed",

            "задержанные": "delayed",
            "задержан": "delayed",
            "задержка": "delayed",
            "задержки": "delayed",
            "отмененные": "cancelled",
            "отменённые": "cancelled",
            "отменен": "cancelled",
            "отменён": "cancelled",
            "отмена": "cancelled",
            "отмены": "cancelled",
            "в полете": "in air",
            "в полёте": "in air",
            "летит": "in air",
            "летят": "in air",
            "приземлился": "landed",
            "приземлились": "landed",
            "прибыл": "landed",
            "прибыли": "landed",

            "требует внимания": "needs attention",
            "требуют внимания": "needs attention",
            "приоритетные": "priority",
            "приоритет": "priority",
            "критические": "critical",
            "критический": "critical",
            "проблемные": "critical",

            "топ": "top",
            "самый": "most",
            "самая": "most",
            "самые": "most",
            "больше всего": "most",

            "база данных": "database",
            "структура базы": "database structure",
            "таблица": "table",
            "таблицы": "tables",
            "модель": "model",
            "модели": "models",
        }

        for old in sorted(replacements.keys(), key=len, reverse=True):
            value = value.replace(old, replacements[old])

        value = re.sub(r"[^\w\s\-]", " ", value, flags=re.UNICODE)
        value = re.sub(r"\s+", " ", value).strip()

        return value

    def _remove_accents(self, value: str) -> str:
        normalized = unicodedata.normalize("NFD", value)

        return "".join(
            character
            for character in normalized
            if unicodedata.category(character) != "Mn"
        )

    def _detect_metric(self, normalized: str) -> str | None:
        for metric_key, config in COPILOT_SUPPORTED_METRICS.items():
            for keyword in config.get("keywords", []):
                clean_keyword = self._remove_accents(keyword.lower())

                if clean_keyword in normalized:
                    return metric_key

        return None

    def _contains_any(self, normalized: str, patterns: list[str]) -> bool:
        return any(pattern in normalized for pattern in patterns)

    def _is_greeting(self, normalized: str) -> bool:
        return normalized in {
            "hello",
            "hi",
            "hey",
            "bonjour",
            "salut",
            "bonsoir",
            "привет",
            "здравствуйте",
            "добрый день",
        }

    def _is_operational_summary_query(self, normalized: str) -> bool:
        return self._contains_any(
            normalized,
            [
                "summary",
                "overview",
                "current situation",
                "current operational situation",
                "operational situation",
                "current state",
                "system state",
                "active operations",
                "what is happening",
                "what now",
                "state of system",
                "global overview",
                "operational summary",
            ],
        )

    def _is_sync_query(self, normalized: str) -> bool:
        return self._contains_any(
            normalized,
            [
                "sync",
                "api sync",
                "sync status",
                "latest sync",
                "last sync",
                "data sync",
                "synchronization",
                "api status",
                "provider status",
                "provider health",
                "sync failed",
                "failed sync",
                "import status",
            ],
        )

    def _is_priority_query(self, normalized: str) -> bool:
        return self._contains_any(
            normalized,
            [
                "priority",
                "needs attention",
                "need attention",
                "require attention",
                "requires attention",
                "to review",
                "review flights",
                "what should i check",
                "what needs attention",
            ],
        )

    def _is_critical_query(self, normalized: str) -> bool:
        return self._contains_any(
            normalized,
            [
                "critical",
                "critical attention",
                "critical flights",
                "high risk",
                "risk flights",
                "problematic flights",
                "disruption signals",
            ],
        )

    def _is_source_breakdown_query(self, normalized: str) -> bool:
        return self._contains_any(
            normalized,
            [
                "source breakdown",
                "source distribution",
                "sources distribution",
                "data sources",
                "data origin",
                "api and local",
                "local and api",
                "external and local",
            ],
        )

    def _is_module_routing_query(self, normalized: str) -> bool:
        return self._contains_any(
            normalized,
            [
                "which module",
                "what module",
                "where should i check",
                "where to check",
                "where should i go",
                "which page",
                "what should i open",
                "recommended module",
                "open module",
            ],
        )

    def _is_top_airline_query(self, normalized: str) -> bool:
        return (
            "top airline" in normalized
            or "busiest airline" in normalized
            or ("airline" in normalized and "most" in normalized)
            or ("airlines" in normalized and "most" in normalized)
        )

    def _is_top_airport_query(self, normalized: str) -> bool:
        return (
            "top airport" in normalized
            or "busiest airport" in normalized
            or ("airport" in normalized and "most" in normalized)
            or ("airports" in normalized and "most" in normalized)
        )

    def _is_top_route_query(self, normalized: str) -> bool:
        return (
            "top route" in normalized
            or "busiest route" in normalized
            or ("route" in normalized and "most" in normalized)
            or ("routes" in normalized and "most" in normalized)
        )

    def _is_today_flights_query(self, normalized: str) -> bool:
        return (
            ("today" in normalized or "now" in normalized)
            and ("flight" in normalized or "flights" in normalized)
        )

    def _extract_status(self, normalized: str) -> str | None:
        has_flight_context = (
            "flight" in normalized
            or "flights" in normalized
            or "status" in normalized
            or "show me" in normalized
            or "how many" in normalized
        )

        if not has_flight_context:
            return None

        for status, aliases in self.STATUS_ALIASES.items():
            for alias in aliases:
                if self._normalize(alias) in normalized:
                    return status

        return None

    def _extract_airline_name(self, normalized: str) -> str | None:
        patterns = [
            r"flights of (?P<value>.+)$",
            r"flights for (?P<value>.+)$",
            r"flights by (?P<value>.+)$",
            r"show flights for (?P<value>.+)$",
            r"show me flights for (?P<value>.+)$",
            r"airline (?P<value>.+)$",
        ]

        for pattern in patterns:
            match = re.search(pattern, normalized)

            if match:
                value = match.group("value").strip()

                if value:
                    return value

        return None

    def _is_metric_explanation_query(
        self,
        normalized: str,
        metric_key: str | None,
    ) -> bool:
        if metric_key:
            return True

        return self._contains_any(
            normalized,
            [
                "explain",
                "what is",
                "what does",
                "definition",
                "meaning",
                "how to read",
                "c est quoi",
                "explique",
                "signifie",
                "что значит",
                "объясни",
                "значение",
            ],
        )

    def _is_database_dictionary_query(self, normalized: str) -> bool:
        return self._contains_any(
            normalized,
            [
                "database",
                "database structure",
                "dictionary",
                "schema",
                "table",
                "tables",
                "model",
                "models",
                "base de donne",
                "base de données",
                "dictionnaire",
            ],
        )

    def _looks_like_operational_question(self, normalized: str) -> bool:
        business_tokens = [
            "flight",
            "flights",
            "status",
            "route",
            "routes",
            "airport",
            "airports",
            "airline",
            "airlines",
            "sync",
            "api",
            "source",
            "sources",
            "delayed",
            "cancelled",
            "critical",
            "priority",
            "operations",
            "operational",
        ]

        question_tokens = [
            "show",
            "show me",
            "how many",
            "which",
            "what",
            "where",
            "list",
            "give",
            "summary",
            "overview",
        ]

        return (
            any(token in normalized for token in business_tokens)
            and any(token in normalized for token in question_tokens)
        )