class CopilotLanguageService:
    """
    Detects the user's language and provides controlled multilingual text.

    Supported languages:
    - en: English
    - fr: French
    - ru: Russian

    The service keeps Copilot answers aligned with the user's language while
    using only controlled project data.
    """

    SUPPORTED_LANGUAGES = {"en", "fr", "ru"}

    def detect_language(self, message: str) -> str:
        value = (message or "").strip().lower()

        if not value:
            return "en"

        if self._contains_cyrillic(value):
            return "ru"

        french_markers = [
            "bonjour",
            "salut",
            "bonsoir",
            "résumé",
            "resume",
            "situation",
            "opération",
            "operation",
            "opérationnel",
            "operationnel",
            "retard",
            "retards",
            "annulé",
            "annule",
            "annulés",
            "annules",
            "vol",
            "vols",
            "compagnie",
            "aéroport",
            "aeroport",
            "synchronisation",
            "données",
            "donnees",
            "base de données",
            "base de donnees",
            "quels",
            "quelle",
            "combien",
            "montre",
            "donne",
            "explique",
        ]

        if any(marker in value for marker in french_markers):
            return "fr"

        return "en"

    def _contains_cyrillic(self, value: str) -> bool:
        return any("\u0400" <= char <= "\u04ff" for char in value)

    def text(self, key: str, language: str = "en", **kwargs) -> str:
        language = language if language in self.SUPPORTED_LANGUAGES else "en"

        templates = {
            "empty_title": {
                "en": "Write an operational question",
                "fr": "Écris une question opérationnelle",
                "ru": "Введите операционный вопрос",
            },
            "empty_request": {
                "en": (
                    "Write an operational question and I will read the system data for you. "
                    "For example: current operational summary, delayed flights, API sync status, "
                    "busiest route, or database structure."
                ),
                "fr": (
                    "Écris une question opérationnelle et je lirai les données du système pour toi. "
                    "Par exemple : résumé opérationnel, vols retardés, statut de synchronisation API, "
                    "route la plus active ou structure de la base de données."
                ),
                "ru": (
                    "Напишите операционный вопрос, и я прочитаю данные системы. "
                    "Например: текущая сводка операций, задержанные рейсы, статус синхронизации API, "
                    "самый активный маршрут или структура базы данных."
                ),
            },
            "greeting_title": {
                "en": "Operational Copilot",
                "fr": "Copilot opérationnel",
                "ru": "Операционный Copilot",
            },
            "greeting_message": {
                "en": "Hello. I am ready to help you read the flight operations system.",
                "fr": "Bonjour. Je suis prêt à t’aider à analyser le système d’exploitation des vols.",
                "ru": "Здравствуйте. Я готов помочь вам проанализировать систему управления авиарейсами.",
            },
            "greeting_bullet_total": {
                "en": "The system currently contains {total_flights} flight records.",
                "fr": "Le système contient actuellement {total_flights} enregistrements de vols.",
                "ru": "В системе сейчас содержится {total_flights} записей о рейсах.",
            },
            "greeting_bullet_active": {
                "en": "Active movement: {active_count} flights.",
                "fr": "Mouvement actif : {active_count} vols.",
                "ru": "Активное движение: {active_count} рейсов.",
            },
            "greeting_bullet_delayed": {
                "en": "Delayed flights: {delayed_count}.",
                "fr": "Vols retardés : {delayed_count}.",
                "ru": "Задержанные рейсы: {delayed_count}.",
            },
            "greeting_bullet_cancelled": {
                "en": "Cancelled flights: {cancelled_count}.",
                "fr": "Vols annulés : {cancelled_count}.",
                "ru": "Отменённые рейсы: {cancelled_count}.",
            },
            "greeting_bullet_scope": {
                "en": (
                    "You can ask me about operations, delays, cancellations, routes, airlines, "
                    "airports, data sources or API synchronization."
                ),
                "fr": (
                    "Tu peux me poser des questions sur les opérations, les retards, les annulations, "
                    "les routes, les compagnies, les aéroports, les sources de données ou la synchronisation API."
                ),
                "ru": (
                    "Вы можете спрашивать меня об операциях, задержках, отменах, маршрутах, "
                    "авиакомпаниях, аэропортах, источниках данных и синхронизации API."
                ),
            },
            "operational_summary_title": {
                "en": "Operational summary",
                "fr": "Résumé opérationnel",
                "ru": "Операционная сводка",
            },
            "operational_summary_no_data": {
                "en": "No flight records are currently available in the system.",
                "fr": "Aucun enregistrement de vol n’est actuellement disponible dans le système.",
                "ru": "В системе сейчас нет доступных записей о рейсах.",
            },
            "operational_summary_message_attention": {
                "en": (
                    "The system currently tracks {total_flights} flights. "
                    "{active_count} records are operationally active. "
                    "{critical_count} records need attention because they are delayed or cancelled."
                ),
                "fr": (
                    "Le système suit actuellement {total_flights} vols. "
                    "{active_count} enregistrements sont opérationnellement actifs. "
                    "{critical_count} enregistrements nécessitent une attention particulière parce qu’ils sont retardés ou annulés."
                ),
                "ru": (
                    "Система сейчас отслеживает {total_flights} рейсов. "
                    "{active_count} записей остаются операционно активными. "
                    "{critical_count} записей требуют внимания, потому что они задержаны или отменены."
                ),
            },
            "operational_summary_message_stable": {
                "en": (
                    "The system currently tracks {total_flights} flights. "
                    "{active_count} records are active, and no delayed or cancelled records are visible in the current snapshot."
                ),
                "fr": (
                    "Le système suit actuellement {total_flights} vols. "
                    "{active_count} enregistrements sont actifs, et aucun vol retardé ou annulé n’est visible dans l’état actuel."
                ),
                "ru": (
                    "Система сейчас отслеживает {total_flights} рейсов. "
                    "{active_count} записей активны, и в текущем состоянии нет видимых задержанных или отменённых рейсов."
                ),
            },
            "situation_pressure": {
                "en": "There is visible disruption pressure in the current dataset.",
                "fr": "Il existe une pression opérationnelle visible dans les données actuelles.",
                "ru": "В текущем наборе данных видна операционная нагрузка из-за нарушений.",
            },
            "situation_stable": {
                "en": "The current snapshot looks stable under the current disruption rule.",
                "fr": "L’état actuel semble stable selon la règle de perturbation utilisée.",
                "ru": "Текущее состояние выглядит стабильным по действующему правилу нарушений.",
            },
            "delayed_count": {
                "en": "Delayed flights: {delayed_count}.",
                "fr": "Vols retardés : {delayed_count}.",
                "ru": "Задержанные рейсы: {delayed_count}.",
            },
            "cancelled_count": {
                "en": "Cancelled flights: {cancelled_count}.",
                "fr": "Vols annulés : {cancelled_count}.",
                "ru": "Отменённые рейсы: {cancelled_count}.",
            },
            "live_tracked_count": {
                "en": "Live tracked flights: {live_tracked_count}.",
                "fr": "Vols suivis avec position : {live_tracked_count}.",
                "ru": "Рейсы с доступным отслеживанием: {live_tracked_count}.",
            },
            "dominant_status": {
                "en": "Dominant status: {dominant_status}.",
                "fr": "Statut dominant : {dominant_status}.",
                "ru": "Доминирующий статус: {dominant_status}.",
            },
            "delay_rate": {
                "en": "Delay rate: {delay_rate}%.",
                "fr": "Taux de retard : {delay_rate}%.",
                "ru": "Процент задержек: {delay_rate}%.",
            },
            "cancellation_rate": {
                "en": "Cancellation rate: {cancellation_rate}%.",
                "fr": "Taux d’annulation : {cancellation_rate}%.",
                "ru": "Процент отмен: {cancellation_rate}%.",
            },
            "stored_data_note": {
                "en": "This reading is based on stored system records, not on external live web data.",
                "fr": (
                    "Cette analyse est basée sur les données enregistrées dans le système, "
                    "pas sur des données web externes en temps réel."
                ),
                "ru": (
                    "Этот анализ основан на данных, сохранённых в системе, "
                    "а не на внешних онлайн-данных в реальном времени."
                ),
            },
            "api_sync_title": {
                "en": "API sync status",
                "fr": "Statut de synchronisation API",
                "ru": "Статус синхронизации API",
            },
            "delayed_title": {
                "en": "Delayed flights",
                "fr": "Vols retardés",
                "ru": "Задержанные рейсы",
            },
            "delayed_none": {
                "en": "No delayed flights are currently recorded in the system.",
                "fr": "Aucun vol retardé n’est actuellement enregistré dans le système.",
                "ru": "В системе сейчас нет задержанных рейсов.",
            },
            "delayed_found": {
                "en": "There are currently {total_count} delayed flights in the system.",
                "fr": "Il y a actuellement {total_count} vols retardés dans le système.",
                "ru": "В системе сейчас {total_count} задержанных рейсов.",
            },
            "cancelled_title": {
                "en": "Cancelled flights",
                "fr": "Vols annulés",
                "ru": "Отменённые рейсы",
            },
            "cancelled_none": {
                "en": "No cancelled flights are currently recorded in the system.",
                "fr": "Aucun vol annulé n’est actuellement enregistré dans le système.",
                "ru": "В системе сейчас нет отменённых рейсов.",
            },
            "cancelled_found": {
                "en": "There are currently {total_count} cancelled flights in the system.",
                "fr": "Il y a actuellement {total_count} vols annulés dans le système.",
                "ru": "В системе сейчас {total_count} отменённых рейсов.",
            },
            "priority_title": {
                "en": "Priority flights",
                "fr": "Vols prioritaires",
                "ru": "Приоритетные рейсы",
            },
            "priority_none": {
                "en": "No flight currently requires priority attention.",
                "fr": "Aucun vol ne nécessite actuellement une attention prioritaire.",
                "ru": "Сейчас нет рейсов, требующих приоритетного внимания.",
            },
            "priority_found": {
                "en": "{count} flights currently require priority attention.",
                "fr": "{count} vols nécessitent actuellement une attention prioritaire.",
                "ru": "{count} рейсов сейчас требуют приоритетного внимания.",
            },
            "critical_title": {
                "en": "Critical attention",
                "fr": "Attention critique",
                "ru": "Критическое внимание",
            },
            "source_breakdown_title": {
                "en": "Data source breakdown",
                "fr": "Répartition des sources de données",
                "ru": "Распределение источников данных",
            },
            "database_title": {
                "en": "Database structure",
                "fr": "Structure de la base de données",
                "ru": "Структура базы данных",
            },
            "database_message": {
                "en": "The system relies on operational flight records, reference data and synchronization logs.",
                "fr": (
                    "Le système s’appuie sur les enregistrements de vols, "
                    "les données de référence et les journaux de synchronisation."
                ),
                "ru": (
                    "Система опирается на записи рейсов, справочные данные "
                    "и журналы синхронизации."
                ),
            },
            "api_sync_no_log": {
                "en": "No API synchronization log is currently available.",
                "fr": "Aucun journal de synchronisation API n’est actuellement disponible.",
                "ru": "Сейчас нет доступного журнала синхронизации API.",
            },
            "api_sync_failed": {
                "en": (
                    "The latest {latest_provider} synchronization needs review. "
                    "Type: {latest_sync_type}. Status: {latest_status}."
                ),
                "fr": (
                    "La dernière synchronisation {latest_provider} nécessite une vérification. "
                    "Type : {latest_sync_type}. Statut : {latest_status}."
                ),
                "ru": (
                    "Последняя синхронизация {latest_provider} требует проверки. "
                    "Тип: {latest_sync_type}. Статус: {latest_status}."
                ),
            },
            "api_sync_success": {
                "en": "The latest {latest_provider} synchronization completed with status: {latest_status}.",
                "fr": "La dernière synchronisation {latest_provider} s’est terminée avec le statut : {latest_status}.",
                "ru": "Последняя синхронизация {latest_provider} завершилась со статусом: {latest_status}.",
            },
            "unknown_title": {
                "en": "I need a clearer operational question",
                "fr": "J’ai besoin d’une question opérationnelle plus claire",
                "ru": "Мне нужен более точный операционный вопрос",
            },
            "unknown_message": {
                "en": (
                    "I could not match this request to a supported operational intent. "
                    "Ask me about flight status, delays, cancellations, priority records, routes, airlines, airports, "
                    "data sources, API synchronization, or database meaning."
                ),
                "fr": (
                    "Je n’ai pas pu associer cette demande à une intention opérationnelle prise en charge. "
                    "Pose-moi une question sur les statuts des vols, les retards, les annulations, les vols prioritaires, "
                    "les routes, les compagnies, les aéroports, les sources de données, la synchronisation API ou la base de données."
                ),
                "ru": (
                    "Я не смог связать этот запрос с поддерживаемой операционной задачей. "
                    "Спросите меня о статусах рейсов, задержках, отменах, приоритетных записях, маршрутах, авиакомпаниях, "
                    "аэропортах, источниках данных, синхронизации API или структуре базы данных."
                ),
            },
        }

        template = templates.get(key, {}).get(language) or templates.get(key, {}).get("en") or key

        try:
            return template.format(**kwargs)
        except Exception:
            return template