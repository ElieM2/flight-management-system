(function () {
    "use strict";

    function ready(callback) {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", callback);
            return;
        }

        callback();
    }

    ready(function () {
        const panel = document.getElementById("copilotPanel");

        if (!panel) {
            return;
        }

        const endpoint = "/copilot/ask/";

        const thread = document.getElementById("copilotThread");
        const threadInner = document.getElementById("copilotThreadInner");
        const messageInput = document.getElementById("copilotMessage");
        const submitButton = document.getElementById("copilotSubmitButton");
        const clearButton = document.getElementById("copilotClearButton");
        const welcomeMessage = document.getElementById("copilotWelcomeMessage");
        const historyList = document.getElementById("copilotHistoryList");

        const userTemplate = document.getElementById("copilotUserMessageTemplate");
        const loadingTemplate = document.getElementById("copilotResponseLoadingTemplate");
        const errorTemplate = document.getElementById("copilotResponseErrorTemplate");
        const responseTemplate = document.getElementById("copilotResponseTemplate");

        const quickRequestButtons = document.querySelectorAll(".copilot-quick-request, [data-copilot-request], [data-request]");
        const openButtons = document.querySelectorAll("[data-copilot-open]");

        const COPILOT_STORAGE_KEY = "logosflight_copilot_messages_v1";
        const COPILOT_REQUEST_HISTORY_KEY = "logosflight_copilot_request_history_v1";

        let currentLoadingNode = null;
        let conversationHistory = [];
        let isSending = false;
        let isRestoringConversation = false;

        const DATE_KEYS = new Set([
            "scheduled_departure",
            "scheduled_arrival",
            "actual_departure",
            "actual_arrival",
            "started_at",
            "finished_at",
            "last_synced_at",
            "created_at",
            "updated_at"
        ]);

        const IMPORTANT_METRIC_ORDER = [
            "total_flights",
            "active_count",
            "delayed_count",
            "cancelled_count",
            "critical_count",
            "delay_rate",
            "cancellation_rate",
            "api_flights",
            "local_flights",
            "api_rate",
            "local_rate",
            "success_rate",
            "failure_rate",
            "failed_count",
            "total_records_received",
            "total_records_created",
            "total_records_updated",
            "live_tracked_count",
            "live_tracked_rate"
        ];

        function readStoredMessages() {
            try {
                const raw = window.localStorage.getItem(COPILOT_STORAGE_KEY);
                const parsed = raw ? JSON.parse(raw) : [];

                return Array.isArray(parsed) ? parsed : [];
            } catch (error) {
                return [];
            }
        }

        function writeStoredMessages(items) {
            try {
                window.localStorage.setItem(
                    COPILOT_STORAGE_KEY,
                    JSON.stringify(items.slice(-40))
                );
            } catch (error) {
                console.warn("Operational Copilot: conversation could not be saved.", error);
            }
        }

        function pushStoredMessage(item) {
            if (isRestoringConversation) {
                return;
            }

            const items = readStoredMessages();

            items.push({
                ...item,
                saved_at: new Date().toISOString()
            });

            writeStoredMessages(items);
        }

        function clearStoredMessages() {
            try {
                window.localStorage.removeItem(COPILOT_STORAGE_KEY);
            } catch (error) {
                console.warn("Operational Copilot: conversation could not be cleared.", error);
            }
        }

        function readStoredRequestHistory() {
            try {
                const raw = window.localStorage.getItem(COPILOT_REQUEST_HISTORY_KEY);
                const parsed = raw ? JSON.parse(raw) : [];

                return Array.isArray(parsed) ? parsed : [];
            } catch (error) {
                return [];
            }
        }

        function writeStoredRequestHistory(items) {
            try {
                window.localStorage.setItem(
                    COPILOT_REQUEST_HISTORY_KEY,
                    JSON.stringify(items.slice(-10))
                );
            } catch (error) {
                console.warn("Operational Copilot: request history could not be saved.", error);
            }
        }

        function clearStoredRequestHistory() {
            try {
                window.localStorage.removeItem(COPILOT_REQUEST_HISTORY_KEY);
            } catch (error) {
                console.warn("Operational Copilot: request history could not be cleared.", error);
            }
        }

        function restoreStoredConversation() {
            const items = readStoredMessages();

            if (!items.length) {
                return;
            }

            if (welcomeMessage) {
                welcomeMessage.hidden = true;
            }

            isRestoringConversation = true;

            items.forEach(function (item) {
                if (!item || !item.role) {
                    return;
                }

                if (item.role === "user" && item.text) {
                    addUserMessage(item.text);
                    return;
                }

                if (item.role === "response" && item.data) {
                    addOperationalResponse(item.data);
                    return;
                }

                if (item.role === "error" && item.text) {
                    addOperationalError(item.text);
                }
            });

            isRestoringConversation = false;
            scrollThreadToBottom();
        }

        function hasRequiredChatElements() {
            return Boolean(
                thread &&
                threadInner &&
                messageInput &&
                submitButton &&
                userTemplate &&
                loadingTemplate &&
                errorTemplate &&
                responseTemplate
            );
        }

        function getCopilotRoot() {
            return panel.closest(".copilot-bot-page") || panel;
        }

        function openCopilot() {
            const root = getCopilotRoot();

            if (!root) {
                return;
            }

            root.classList.add("is-chat-open");

            window.setTimeout(function () {
                if (messageInput) {
                    messageInput.focus();
                }
            }, 80);
        }

        function closeCopilot() {
            const root = getCopilotRoot();

            if (!root) {
                return;
            }

            root.classList.remove("is-chat-open");
        }

        function toggleExpanded() {
            const root = getCopilotRoot();

            if (!root) {
                return;
            }

            root.classList.toggle("is-expanded");
        }

        function scrollThreadToBottom() {
            if (!thread) {
                return;
            }

            requestAnimationFrame(function () {
                thread.scrollTop = thread.scrollHeight;
            });
        }

        function getCurrentInterfaceLanguage() {
            const htmlLang = (document.documentElement.getAttribute("lang") || "").toLowerCase();
            const selectedLanguage = (document.documentElement.getAttribute("data-language") || "").toLowerCase();

            if (htmlLang.startsWith("fr") || selectedLanguage.startsWith("fr")) {
                return "fr";
            }

            if (htmlLang.startsWith("ru") || selectedLanguage.startsWith("ru")) {
                return "ru";
            }

            const languageButton = document.querySelector("[data-current-language], .language-switcher, .dropdown-toggle");

            if (languageButton) {
                const text = (languageButton.textContent || "").trim().toLowerCase();

                if (text.includes("fr")) {
                    return "fr";
                }

                if (text.includes("ru")) {
                    return "ru";
                }
            }

            return "en";
        }

        function getLocalizedLabel(value) {
            const language = getCurrentInterfaceLanguage();

            const labels = {
                en: {
                    id: "ID",
                    total_flights: "Total flights",
                    scheduled_count: "Scheduled",
                    boarding_count: "Boarding",
                    departed_count: "Departed",
                    in_air_count: "In air",
                    landed_count: "Landed",
                    delayed_count: "Delayed",
                    cancelled_count: "Cancelled",
                    active_count: "Active",
                    completed_count: "Completed",
                    critical_count: "Needs attention",
                    api_flights: "API flights",
                    local_flights: "Local flights",
                    live_tracked_count: "Live tracked",
                    live_tracked_rate: "Live tracked rate",
                    delay_rate: "Delay rate",
                    cancellation_rate: "Cancellation rate",
                    active_rate: "Active rate",
                    api_rate: "API rate",
                    local_rate: "Local rate",
                    dominant_status: "Dominant status",
                    total_logs: "Sync logs",
                    success_count: "Successful logs",
                    failed_count: "Needs review",
                    success_rate: "Success rate",
                    failure_rate: "Review rate",
                    total_records_received: "Records received",
                    total_records_created: "Records created",
                    total_records_updated: "Records updated",
                    latest_log: "Latest log",
                    last_successful_log: "Last successful sync",
                    metric_key: "Metric key",
                    metric_label: "Metric label",
                    scheduled_departure: "Scheduled departure",
                    scheduled_arrival: "Scheduled arrival",
                    actual_departure: "Actual departure",
                    actual_arrival: "Actual arrival",
                    started_at: "Started at",
                    finished_at: "Finished at",
                    last_synced_at: "Last synced",
                    records_received: "Records received",
                    records_created: "Records created",
                    records_updated: "Records updated",
                    provider_name: "Provider",
                    sync_type: "Sync type",
                    status_label: "Status",
                    source_type_label: "Source",
                    high: "High",
                    medium: "Medium",
                    low: "Low"
                },
                fr: {
                    id: "ID",
                    total_flights: "Total des vols",
                    scheduled_count: "Planifiés",
                    boarding_count: "Embarquement",
                    departed_count: "Partis",
                    in_air_count: "En vol",
                    landed_count: "Atterris",
                    delayed_count: "Retardés",
                    cancelled_count: "Annulés",
                    active_count: "Actifs",
                    completed_count: "Terminés",
                    critical_count: "À surveiller",
                    api_flights: "Vols API",
                    local_flights: "Vols locaux",
                    live_tracked_count: "Suivis en direct",
                    live_tracked_rate: "Taux de suivi",
                    delay_rate: "Taux de retard",
                    cancellation_rate: "Taux d’annulation",
                    active_rate: "Taux actif",
                    api_rate: "Part API",
                    local_rate: "Part locale",
                    dominant_status: "Statut dominant",
                    total_logs: "Journaux de synchronisation",
                    success_count: "Synchronisations réussies",
                    failed_count: "À vérifier",
                    success_rate: "Taux de réussite",
                    failure_rate: "Taux à vérifier",
                    total_records_received: "Données reçues",
                    total_records_created: "Données créées",
                    total_records_updated: "Données mises à jour",
                    latest_log: "Dernier journal",
                    last_successful_log: "Dernière synchronisation réussie",
                    metric_key: "Clé métrique",
                    metric_label: "Libellé métrique",
                    scheduled_departure: "Départ prévu",
                    scheduled_arrival: "Arrivée prévue",
                    actual_departure: "Départ réel",
                    actual_arrival: "Arrivée réelle",
                    started_at: "Début",
                    finished_at: "Fin",
                    last_synced_at: "Dernière synchronisation",
                    records_received: "Données reçues",
                    records_created: "Données créées",
                    records_updated: "Données mises à jour",
                    provider_name: "Fournisseur",
                    sync_type: "Type de synchronisation",
                    status_label: "Statut",
                    source_type_label: "Source",
                    high: "Élevé",
                    medium: "Moyen",
                    low: "Faible"
                },
                ru: {
                    id: "ID",
                    total_flights: "Всего рейсов",
                    scheduled_count: "Запланировано",
                    boarding_count: "Посадка",
                    departed_count: "Вылетели",
                    in_air_count: "В полёте",
                    landed_count: "Приземлились",
                    delayed_count: "Задержаны",
                    cancelled_count: "Отменены",
                    active_count: "Активные",
                    completed_count: "Завершены",
                    critical_count: "Требуют внимания",
                    api_flights: "Рейсы API",
                    local_flights: "Локальные рейсы",
                    live_tracked_count: "Отслеживаются",
                    live_tracked_rate: "Доля отслеживания",
                    delay_rate: "Процент задержек",
                    cancellation_rate: "Процент отмен",
                    active_rate: "Активность",
                    api_rate: "Доля API",
                    local_rate: "Локальная доля",
                    dominant_status: "Основной статус",
                    total_logs: "Журналы синхронизации",
                    success_count: "Успешные синхронизации",
                    failed_count: "На проверку",
                    success_rate: "Успешность",
                    failure_rate: "Процент проверки",
                    total_records_received: "Получено записей",
                    total_records_created: "Создано записей",
                    total_records_updated: "Обновлено записей",
                    latest_log: "Последний журнал",
                    last_successful_log: "Последняя успешная синхронизация",
                    metric_key: "Ключ метрики",
                    metric_label: "Название метрики",
                    scheduled_departure: "Плановый вылет",
                    scheduled_arrival: "Плановое прибытие",
                    actual_departure: "Фактический вылет",
                    actual_arrival: "Фактическое прибытие",
                    started_at: "Начало",
                    finished_at: "Конец",
                    last_synced_at: "Последняя синхронизация",
                    records_received: "Получено записей",
                    records_created: "Создано записей",
                    records_updated: "Обновлено записей",
                    provider_name: "Поставщик",
                    sync_type: "Тип синхронизации",
                    status_label: "Статус",
                    source_type_label: "Источник",
                    high: "Высокий",
                    medium: "Средний",
                    low: "Низкий"
                }
            };

            const dictionary = labels[language] || labels.en;

            return dictionary[value] || labels.en[value] || null;
        }

        function normalizeLabel(value) {
            if (!value) {
                return "N/A";
            }

            const key = String(value).trim();
            const localized = getLocalizedLabel(key);

            if (localized) {
                return localized;
            }

            return key
                .replace(/_/g, " ")
                .replace(/\b\w/g, function (char) {
                    return char.toUpperCase();
                });
        }

        function isIsoDateString(value) {
            if (typeof value !== "string") {
                return false;
            }

            const trimmed = value.trim();

            return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(trimmed) ||
                /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}/.test(trimmed);
        }

        function formatDateTime(value) {
            if (!value) {
                return "N/A";
            }

            try {
                const normalized = String(value).replace(" ", "T");
                const date = new Date(normalized);

                if (Number.isNaN(date.getTime())) {
                    return String(value);
                }

                return new Intl.DateTimeFormat("en-GB", {
                    year: "numeric",
                    month: "short",
                    day: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit"
                }).format(date);
            } catch (error) {
                return String(value);
            }
        }

        function formatPrimitive(value, key) {
            if (value === null || value === undefined || value === "") {
                return "N/A";
            }

            if (typeof value === "boolean") {
                return value ? "Yes" : "No";
            }

            if (typeof value === "number") {
                return String(value);
            }

            if ((key && DATE_KEYS.has(key)) || isIsoDateString(value)) {
                return formatDateTime(value);
            }

            return String(value);
        }

        function createNodeFromTemplate(template) {
            if (!template || !template.content || !template.content.firstElementChild) {
                return null;
            }

            return template.content.firstElementChild.cloneNode(true);
        }

        function cleanMessage(message) {
            return (message || "").trim();
        }

        function getRequestFromElement(element) {
            return cleanMessage(
                element.getAttribute("data-copilot-request") ||
                element.getAttribute("data-request") ||
                ""
            );
        }

        function setTextIfExists(selector, value) {
            const element = document.querySelector(selector);

            if (!element || !value) {
                return;
            }

            element.textContent = value;
        }

        function setRequestButtonText(buttonIndex, value, requestValue) {
            const buttons = Array.from(document.querySelectorAll(".copilot-sidebar-section .copilot-quick-request"));

            if (!buttons[buttonIndex]) {
                return;
            }

            buttons[buttonIndex].textContent = value;

            if (requestValue) {
                buttons[buttonIndex].setAttribute("data-request", requestValue);
                buttons[buttonIndex].setAttribute("data-copilot-request", requestValue);
            }
        }

        function setCompactRequestText(buttonIndex, value, requestValue) {
            const buttons = Array.from(document.querySelectorAll(".copilot-compact-requests .copilot-quick-request"));

            if (!buttons[buttonIndex]) {
                return;
            }

            buttons[buttonIndex].textContent = value;

            if (requestValue) {
                buttons[buttonIndex].setAttribute("data-request", requestValue);
                buttons[buttonIndex].setAttribute("data-copilot-request", requestValue);
            }
        }

        function localizeCopilotStaticInterface() {
            const language = getCurrentInterfaceLanguage();

            const copy = {
                en: {
                    sidebarKicker: "Operational Copilot",
                    sidebarTitle: "Ask the system",
                    sidebarText: "Use the Copilot to review flight operations, synchronization health, route activity and disruption signals.",
                    quickLabel: "Quick actions",
                    recentLabel: "recent requests",
                    sidebarNote: "The Copilot uses validated Django business logic and internal operational data.",
                    headerKicker: "Operations support",
                    headerTitle: "Operational Copilot",
                    headerSubtitle: "Flights, monitoring, analytics and synchronization",
                    clear: "Clear",
                    ready: "Ready",
                    welcomeTitle: "How can I help with flight operations?",
                    welcomeText: "Ask about delayed flights, cancellations, priority records, routes, API synchronization, data sources or the current operational summary.",
                    placeholder: "Analyze delays, cancellations, routes and operational indicators.",
                    composerNoteLeft: "Enter to send. Shift + Enter for a new line.",
                    composerNoteRight: "Answers use internal operational data.",
                    quickRequests: [
                        ["Current operational summary", "Give me the current operational summary"],
                        ["Flights needing attention", "Which flights need attention?"],
                        ["API sync status", "What is the API sync status?"],
                        ["Top route by volume", "What is the top route by flight volume?"],
                        ["Delayed flights", "Show delayed flights"],
                        ["Cancelled flights", "Show cancelled flights"]
                    ],
                    compactRequests: [
                        ["Summary", "Give me the current operational summary"],
                        ["Priority", "Which flights need attention?"],
                        ["Sync", "What is the API sync status?"],
                        ["Routes", "What is the top route by flight volume?"]
                    ]
                },
                fr: {
                    sidebarKicker: "Copilot opérationnel",
                    sidebarTitle: "Interroger le système",
                    sidebarText: "Utilisez le Copilot pour consulter les opérations de vol, la synchronisation, l’activité des routes et les signaux de perturbation.",
                    quickLabel: "Actions rapides",
                    recentLabel: "Requêtes récentes",
                    sidebarNote: "Les réponses s’appuient sur les données internes et les règles métier du système Django.",
                    headerKicker: "Support opérationnel",
                    headerTitle: "Copilot opérationnel",
                    headerSubtitle: "Vols, monitoring, analyse et synchronisation",
                    clear: "Effacer",
                    ready: "Prêt",
                    welcomeTitle: "Comment puis-je aider le suivi des opérations de vol ?",
                    welcomeText: "Posez une question sur les retards, les annulations, les vols prioritaires, les routes, la synchronisation API, les sources de données ou le résumé opérationnel.",
                    placeholder: "Analyser les retards, annulations, routes et indicateurs opérationnels.",
                    composerNoteLeft: "Entrée pour envoyer. Maj + Entrée pour une nouvelle ligne.",
                    composerNoteRight: "Les réponses utilisent les données opérationnelles internes.",
                    quickRequests: [
                        ["Résumé opérationnel actuel", "Donne-moi le résumé opérationnel actuel"],
                        ["Vols à surveiller", "Quels vols demandent une attention prioritaire ?"],
                        ["État de la synchronisation API", "Quel est le statut de synchronisation API ?"],
                        ["Route la plus active", "Quelle est la route la plus active ?"],
                        ["Vols retardés", "Montre les vols retardés"],
                        ["Vols annulés", "Montre les vols annulés"]
                    ],
                    compactRequests: [
                        ["Résumé", "Donne-moi le résumé opérationnel actuel"],
                        ["Priorité", "Quels vols demandent une attention prioritaire ?"],
                        ["Sync", "Quel est le statut de synchronisation API ?"],
                        ["Routes", "Quelle est la route la plus active ?"]
                    ]
                },
                ru: {
                    sidebarKicker: "Операционный Copilot",
                    sidebarTitle: "Запрос к системе",
                    sidebarText: "Используйте Copilot для анализа рейсов, синхронизации, активности маршрутов и операционных отклонений.",
                    quickLabel: "Быстрые действия",
                    recentLabel: "Последние запросы",
                    sidebarNote: "Ответы формируются на основе внутренних данных и бизнес-логики системы Django.",
                    headerKicker: "Операционная поддержка",
                    headerTitle: "Операционный Copilot",
                    headerSubtitle: "Рейсы, мониторинг, аналитика и синхронизация",
                    clear: "Очистить",
                    ready: "Готов",
                    welcomeTitle: "Чем помочь в управлении рейсами?",
                    welcomeText: "Спросите о задержках, отменах, приоритетных рейсах, маршрутах, API-синхронизации, источниках данных или общей операционной сводке.",
                    placeholder: "Анализ задержек, отмен, маршрутов и операционных показателей.",
                    composerNoteLeft: "Enter для отправки. Shift + Enter для новой строки.",
                    composerNoteRight: "Ответы основаны на внутренних операционных данных.",
                    quickRequests: [
                        ["Текущая операционная сводка", "Сводка операций"],
                        ["Рейсы, требующие внимания", "Какие рейсы требуют внимания?"],
                        ["Статус API-синхронизации", "Какой статус API-синхронизации?"],
                        ["Самый активный маршрут", "Какой маршрут самый активный?"],
                        ["Задержанные рейсы", "Покажи задержанные рейсы"],
                        ["Отменённые рейсы", "Покажи отменённые рейсы"]
                    ],
                    compactRequests: [
                        ["Сводка", "Сводка операций"],
                        ["Приоритет", "Какие рейсы требуют внимания?"],
                        ["Sync", "Какой статус API-синхронизации?"],
                        ["Маршруты", "Какой маршрут самый активный?"]
                    ]
                }
            };

            const activeCopy = copy[language] || copy.en;

            setTextIfExists(".copilot-sidebar-head .copilot-home-kicker", activeCopy.sidebarKicker);
            setTextIfExists(".copilot-sidebar-head h3", activeCopy.sidebarTitle);
            setTextIfExists(".copilot-sidebar-head p", activeCopy.sidebarText);
            setTextIfExists(".copilot-sidebar-section:nth-of-type(1) .copilot-sidebar-label", activeCopy.quickLabel);
            setTextIfExists(".copilot-sidebar-section:nth-of-type(2) .copilot-sidebar-label", activeCopy.recentLabel);
            setTextIfExists(".copilot-sidebar-note", activeCopy.sidebarNote);

            setTextIfExists(".copilot-chat-header__identity span", activeCopy.headerKicker);
            setTextIfExists(".copilot-chat-header__identity strong", activeCopy.headerTitle);
            setTextIfExists(".copilot-chat-header__identity small", activeCopy.headerSubtitle);
            setTextIfExists("#copilotClearButton", activeCopy.clear);

            setTextIfExists(".copilot-welcome__badge", activeCopy.ready);
            setTextIfExists(".copilot-welcome__title", activeCopy.welcomeTitle);
            setTextIfExists(".copilot-welcome__text", activeCopy.welcomeText);

            if (messageInput) {
                messageInput.setAttribute("placeholder", activeCopy.placeholder);
            }

            const footerItems = document.querySelectorAll(".copilot-composer__footer span");

            if (footerItems[0]) {
                footerItems[0].textContent = activeCopy.composerNoteLeft;
            }

            if (footerItems[1]) {
                footerItems[1].textContent = activeCopy.composerNoteRight;
            }

            activeCopy.quickRequests.forEach(function (item, index) {
                setRequestButtonText(index, item[0], item[1]);
            });

            activeCopy.compactRequests.forEach(function (item, index) {
                setCompactRequestText(index, item[0], item[1]);
            });
        }

        function updateHistoryList() {
            if (!historyList) {
                return;
            }

            historyList.innerHTML = "";

            if (!conversationHistory.length) {
                const empty = document.createElement("div");
                empty.className = "copilot-history__empty";
                empty.textContent = getCurrentInterfaceLanguage() === "fr"
                    ? "Aucune question récente."
                    : getCurrentInterfaceLanguage() === "ru"
                        ? "Пока нет последних запросов."
                        : "No recent requests yet.";

                historyList.appendChild(empty);
                return;
            }

            conversationHistory.slice().reverse().forEach(function (item) {
                const button = document.createElement("button");

                button.type = "button";
                button.className = "copilot-history__item";
                button.textContent = item;

                button.addEventListener("click", function () {
                    setMessageInput(item);
                    openCopilot();
                });

                historyList.appendChild(button);
            });
        }

        function pushHistoryItem(message) {
            const cleaned = cleanMessage(message);

            if (!cleaned) {
                return;
            }

            const existingIndex = conversationHistory.indexOf(cleaned);

            if (existingIndex !== -1) {
                conversationHistory.splice(existingIndex, 1);
            }

            conversationHistory.push(cleaned);

            if (conversationHistory.length > 10) {
                conversationHistory = conversationHistory.slice(conversationHistory.length - 10);
            }

            writeStoredRequestHistory(conversationHistory);
            updateHistoryList();
        }

        function setMessageInput(message) {
            if (!messageInput) {
                return;
            }

            messageInput.value = cleanMessage(message);
            autoResizeTextarea();
            messageInput.focus();
        }

        function addUserMessage(message) {
            const node = createNodeFromTemplate(userTemplate);

            if (!node) {
                return;
            }

            const bubble = node.querySelector(".copilot-user-bubble");

            if (bubble) {
                bubble.textContent = message;
            }

            threadInner.appendChild(node);
            scrollThreadToBottom();

            pushStoredMessage({
                role: "user",
                text: message
            });
        }

        function addLoadingMessage() {
            removeLoadingMessage();

            currentLoadingNode = createNodeFromTemplate(loadingTemplate);

            if (!currentLoadingNode) {
                return;
            }

            threadInner.appendChild(currentLoadingNode);
            scrollThreadToBottom();
        }

        function removeLoadingMessage() {
            if (currentLoadingNode && currentLoadingNode.parentNode) {
                currentLoadingNode.parentNode.removeChild(currentLoadingNode);
            }

            currentLoadingNode = null;
        }

        function sortMetricEntries(entries) {
            return entries.sort(function (a, b) {
                const indexA = IMPORTANT_METRIC_ORDER.indexOf(a[0]);
                const indexB = IMPORTANT_METRIC_ORDER.indexOf(b[0]);

                if (indexA === -1 && indexB === -1) {
                    return a[0].localeCompare(b[0]);
                }

                if (indexA === -1) {
                    return 1;
                }

                if (indexB === -1) {
                    return -1;
                }

                return indexA - indexB;
            });
        }

        function shouldShowMetric(key, value) {
            if (value === null || value === undefined || value === "") {
                return false;
            }

            if (typeof value === "object") {
                return false;
            }

            const hiddenKeys = new Set([
                "latest_log",
                "last_successful_log"
            ]);

            return !hiddenKeys.has(key);
        }

        function renderMetrics(container, metrics) {
            if (!container) {
                return;
            }

            const grid = container.querySelector(".copilot-metrics-grid");

            if (!grid) {
                container.hidden = true;
                return;
            }

            grid.innerHTML = "";

            const entries = sortMetricEntries(
                Object.entries(metrics || {}).filter(function (entry) {
                    return shouldShowMetric(entry[0], entry[1]);
                })
            );

            if (!entries.length) {
                container.hidden = true;
                return;
            }

            entries.slice(0, 12).forEach(function (entry) {
                const key = entry[0];
                const value = entry[1];

                const card = document.createElement("div");
                card.className = "copilot-metric-card";

                const label = document.createElement("div");
                label.className = "copilot-metric-card__label";
                label.textContent = normalizeLabel(key);

                const metricValue = document.createElement("div");
                metricValue.className = "copilot-metric-card__value";
                metricValue.textContent = formatPrimitive(value, key);

                card.appendChild(label);
                card.appendChild(metricValue);
                grid.appendChild(card);
            });

            container.hidden = false;
        }

        function getStatusBadgeClass(record) {
            const status = String(record.status || record.status_label || "").toLowerCase();

            if (status.includes("cancel")) {
                return " is-cancelled";
            }

            if (status.includes("delay")) {
                return " is-delayed";
            }

            if (status.includes("landed") || status.includes("success")) {
                return " is-ready";
            }

            if (status.includes("failed") || status.includes("review")) {
                return " is-review";
            }

            if (status.includes("in_air") || status.includes("in air") || status.includes("boarding") || status.includes("departed")) {
                return " is-active";
            }

            return "";
        }

        function buildRecordMeta(record) {
            const metaItems = [];

            if (record.route) {
                metaItems.push({
                    label: record.route,
                    type: "route"
                });
            }

            if (record.status_label) {
                metaItems.push({
                    label: "Status: " + record.status_label,
                    type: "status"
                });
            }

            if (record.source_type_label) {
                metaItems.push({
                    label: "Source: " + record.source_type_label,
                    type: "source"
                });
            }

            if (record.provider_name) {
                metaItems.push({
                    label: "Provider: " + record.provider_name,
                    type: "provider"
                });
            }

            if (record.sync_type) {
                metaItems.push({
                    label: "Sync: " + record.sync_type,
                    type: "sync"
                });
            }

            if (record.departure_delay_minutes !== undefined && record.departure_delay_minutes !== null) {
                metaItems.push({
                    label: "Delay: " + record.departure_delay_minutes + " min",
                    type: "delay"
                });
            }

            return metaItems;
        }

        function buildRecordTitle(record) {
            if (record.flight_number) {
                return record.flight_number;
            }

            if (record.provider_name && record.sync_type) {
                return record.provider_name + " / " + record.sync_type;
            }

            if (record.provider_name) {
                return record.provider_name;
            }

            return "Operational record";
        }

        function renderRecordDetails(detailsContainer, record) {
            const visibleKeys = [
                "airline",
                "origin_iata",
                "destination_iata",
                "scheduled_departure",
                "scheduled_arrival",
                "actual_departure",
                "actual_arrival",
                "started_at",
                "finished_at",
                "records_received",
                "records_created",
                "records_updated",
                "duration_seconds",
                "message",
                "last_synced_at"
            ];

            visibleKeys.forEach(function (key) {
                if (!(key in record)) {
                    return;
                }

                const value = record[key];

                if (value === null || value === undefined || value === "") {
                    return;
                }

                const row = document.createElement("div");
                row.className = "copilot-record-card__detail-row";

                const label = document.createElement("span");
                label.className = "copilot-record-card__detail-label";
                label.textContent = normalizeLabel(key);

                const detailValue = document.createElement("span");
                detailValue.className = "copilot-record-card__detail-value";
                detailValue.textContent = formatPrimitive(value, key);

                row.appendChild(label);
                row.appendChild(detailValue);
                detailsContainer.appendChild(row);
            });
        }

        function renderRecords(container, records) {
            if (!container) {
                return;
            }

            const list = container.querySelector(".copilot-records-list");

            if (!list) {
                container.hidden = true;
                return;
            }

            list.innerHTML = "";

            if (!records || !records.length) {
                container.hidden = true;
                return;
            }

            records.slice(0, 10).forEach(function (record) {
                const card = document.createElement("article");
                card.className = "copilot-record-card" + getStatusBadgeClass(record);

                const title = document.createElement("h5");
                title.className = "copilot-record-card__title";
                title.textContent = buildRecordTitle(record);

                const meta = document.createElement("div");
                meta.className = "copilot-record-card__meta";

                buildRecordMeta(record).forEach(function (metaItem) {
                    const badge = document.createElement("span");
                    badge.className = "copilot-record-card__badge";
                    badge.textContent = metaItem.label;
                    meta.appendChild(badge);
                });

                const details = document.createElement("div");
                details.className = "copilot-record-card__details";

                renderRecordDetails(details, record);

                card.appendChild(title);

                if (meta.childNodes.length) {
                    card.appendChild(meta);
                }

                if (details.childNodes.length) {
                    card.appendChild(details);
                }

                list.appendChild(card);
            });

            container.hidden = false;
        }

        function renderRecommendation(container, moduleName, moduleUrl) {
            if (!container) {
                return;
            }

            const box = container.querySelector(".copilot-recommendation");

            if (!box) {
                container.hidden = true;
                return;
            }

            box.innerHTML = "";

            if (!moduleName && !moduleUrl) {
                container.hidden = true;
                return;
            }

            const wrapper = document.createElement("div");
            wrapper.className = "copilot-recommendation__content";

            const title = document.createElement("div");
            title.className = "copilot-recommendation__title";
            title.textContent = moduleName || "Recommended module";

            wrapper.appendChild(title);

            if (moduleUrl) {
                const link = document.createElement("a");
                link.className = "copilot-recommendation__link";
                link.href = moduleUrl;
                link.textContent = getCurrentInterfaceLanguage() === "fr"
                    ? "Ouvrir"
                    : getCurrentInterfaceLanguage() === "ru"
                        ? "Открыть"
                        : "Open";

                wrapper.appendChild(link);
            }

            box.appendChild(wrapper);
            container.hidden = false;
        }

        function getDisplayMessage(data) {
            const rewrittenMessage = cleanMessage(data.rewritten_message);
            const originalMessage = cleanMessage(data.message);

            return rewrittenMessage || originalMessage || "The system returned an empty response.";
        }

        function getIntentKey(data) {
            return String(data.intent || "").toLowerCase();
        }

        function isSimpleChatIntent(data) {
            const intent = getIntentKey(data);

            return [
                "copilot_greeting",
                "unknown"
            ].includes(intent);
        }

        function isOperationalListIntent(data) {
            const intent = getIntentKey(data);

            return [
                "delayed_flights",
                "cancelled_flights",
                "priority_flights",
                "critical_attention",
                "flights_by_status",
                "flights_by_airline"
            ].includes(intent);
        }

        function isMetricsHeavyIntent(data) {
            const intent = getIntentKey(data);

            return [
                "operational_summary",
                "api_sync_status",
                "source_breakdown",
                "database_dictionary",
                "top_airline",
                "top_airport",
                "top_route",
                "todays_flights"
            ].includes(intent);
        }

        function setSectionVisibility(section, visible) {
            if (!section) {
                return;
            }

            section.hidden = !visible;
        }

        function hideSection(section) {
            setSectionVisibility(section, false);
        }

        function hasItems(value) {
            return Array.isArray(value) && value.length > 0;
        }

        function hasMetrics(value) {
            if (!value || typeof value !== "object") {
                return false;
            }

            return Object.keys(value).some(function (key) {
                return shouldShowMetric(key, value[key]);
            });
        }

        function shouldShowBulletsForResponse(data) {
            if (isSimpleChatIntent(data)) {
                return false;
            }

            if (isOperationalListIntent(data)) {
                return false;
            }

            return hasItems(data.bullets);
        }

        function shouldShowMetricsForResponse(data) {
            if (isSimpleChatIntent(data)) {
                return false;
            }

            if (isOperationalListIntent(data)) {
                return false;
            }

            return isMetricsHeavyIntent(data) && hasMetrics(data.metrics || {});
        }

        function shouldShowRecordsForResponse(data) {
            if (isSimpleChatIntent(data)) {
                return false;
            }

            return hasItems(data.records);
        }

        function shouldShowRecommendationForResponse(data) {
            if (isSimpleChatIntent(data)) {
                return false;
            }

            if (isOperationalListIntent(data)) {
                return false;
            }

            return Boolean(data.recommended_module || data.recommended_url);
        }

        function shouldShowFooterForResponse(data) {
            return false;
        }

        function addOperationalError(message) {
            const node = createNodeFromTemplate(errorTemplate);

            if (!node) {
                return;
            }

            const errorText = node.querySelector(".copilot-error-text");
            const fallbackMessage = "The request could not be processed.";

            if (errorText) {
                errorText.textContent = message || fallbackMessage;
            }

            threadInner.appendChild(node);
            scrollThreadToBottom();

            pushStoredMessage({
                role: "error",
                text: message || fallbackMessage
            });
        }

        function addOperationalResponse(data) {
            const node = createNodeFromTemplate(responseTemplate);

            if (!node) {
                return;
            }

            const type = node.querySelector(".copilot-response__type");
            const title = node.querySelector(".copilot-response__title");
            const message = node.querySelector(".copilot-response__message");
            const confidence = node.querySelector(".copilot-response__confidence");
            const responseCard = node.querySelector(".copilot-response") || node;

            if (isSimpleChatIntent(data)) {
                node.classList.add("copilot-message-row--simple");
                responseCard.classList.add("copilot-response--simple");
            }

            if (isOperationalListIntent(data)) {
                node.classList.add("copilot-message-row--list");
                responseCard.classList.add("copilot-response--list");
            }

            if (isMetricsHeavyIntent(data)) {
                node.classList.add("copilot-message-row--analytical");
                responseCard.classList.add("copilot-response--analytical");
            }

            if (type) {
                type.textContent = "Operational Copilot";
            }

            if (title) {
                title.textContent = data.title || "Operational answer";
            }

            if (message) {
                message.textContent = getDisplayMessage(data);
            }

            if (confidence) {
                const confidenceValue = String(data.confidence || "high").toLowerCase();

                confidence.textContent = normalizeLabel(confidenceValue);
                confidence.setAttribute("data-confidence", confidenceValue);
            }

            const bulletsSection = node.querySelector(".copilot-response__section--bullets");

            if (bulletsSection) {
                const bulletsList = bulletsSection.querySelector(".copilot-response__bullets");

                if (bulletsList) {
                    bulletsList.innerHTML = "";

                    if (shouldShowBulletsForResponse(data)) {
                        data.bullets.forEach(function (item) {
                            const li = document.createElement("li");
                            li.textContent = item;
                            bulletsList.appendChild(li);
                        });

                        bulletsSection.hidden = false;
                    } else {
                        bulletsSection.hidden = true;
                    }
                }
            }

            const metricsSection = node.querySelector(".copilot-response__section--metrics");
            const recordsSection = node.querySelector(".copilot-response__section--records");
            const recommendationSection = node.querySelector(".copilot-response__section--recommendation");

            if (shouldShowMetricsForResponse(data)) {
                renderMetrics(metricsSection, data.metrics || {});
            } else {
                hideSection(metricsSection);
            }

            if (shouldShowRecordsForResponse(data)) {
                renderRecords(recordsSection, data.records || []);
            } else {
                hideSection(recordsSection);
            }

            if (shouldShowRecommendationForResponse(data)) {
                renderRecommendation(
                    recommendationSection,
                    data.recommended_module,
                    data.recommended_url
                );
            } else {
                hideSection(recommendationSection);
            }

            const footer = node.querySelector(".copilot-response__footer");

            if (footer) {
                if (shouldShowFooterForResponse(data)) {
                    footer.textContent = data.source_note || "";
                    footer.hidden = false;
                } else {
                    footer.textContent = "";
                    footer.hidden = true;
                }
            }

            threadInner.appendChild(node);
            scrollThreadToBottom();

            pushStoredMessage({
                role: "response",
                data: data
            });
        }

        function clearConversation() {
            removeLoadingMessage();

            Array.from(threadInner.children).forEach(function (child) {
                if (child !== welcomeMessage) {
                    child.remove();
                }
            });

            if (welcomeMessage) {
                welcomeMessage.hidden = false;
            }

            if (messageInput) {
                messageInput.value = "";
                messageInput.style.height = "auto";
                messageInput.focus();
            }

            if (!isRestoringConversation) {
                clearStoredMessages();
            }
        }

        function autoResizeTextarea() {
            if (!messageInput) {
                return;
            }

            messageInput.style.height = "auto";
            messageInput.style.height = Math.min(messageInput.scrollHeight, 192) + "px";
        }

        function setComposerState(disabled) {
            if (submitButton) {
                submitButton.disabled = disabled;
            }

            if (messageInput) {
                messageInput.disabled = disabled;
            }
        }

        async function sendMessage(customMessage) {
            if (!hasRequiredChatElements()) {
                console.warn("Operational Copilot: required chat elements are missing.");
                return;
            }

            if (isSending) {
                return;
            }

            const message = cleanMessage(customMessage || messageInput.value);

            if (!message) {
                addOperationalError(
                    getCurrentInterfaceLanguage() === "fr"
                        ? "Écris une question avant d’envoyer."
                        : getCurrentInterfaceLanguage() === "ru"
                            ? "Напишите вопрос перед отправкой."
                            : "Write a question before sending."
                );
                return;
            }

            openCopilot();

            if (welcomeMessage) {
                welcomeMessage.hidden = true;
            }

            pushHistoryItem(message);
            addUserMessage(message);
            addLoadingMessage();

            isSending = true;
            setComposerState(true);

            if (messageInput) {
                messageInput.value = "";
                messageInput.style.height = "auto";
            }

            try {
                const response = await fetch(endpoint, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        message: message
                    })
                });

                let payload = null;

                try {
                    payload = await response.json();
                } catch (jsonError) {
                    throw new Error("The server returned an unreadable response.");
                }

                removeLoadingMessage();

                if (!response.ok || !payload.ok) {
                    throw new Error(payload.error || "The request failed.");
                }

                addOperationalResponse(payload.data || {});
            } catch (error) {
                removeLoadingMessage();
                addOperationalError(error.message || "The system could not return a response.");
            } finally {
                isSending = false;
                setComposerState(false);

                if (messageInput) {
                    messageInput.focus();
                }
            }
        }

        openButtons.forEach(function (button) {
            button.addEventListener("click", function () {
                openCopilot();

                const request = getRequestFromElement(button);

                if (request) {
                    sendMessage(request);
                }
            });
        });

        quickRequestButtons.forEach(function (button) {
            button.addEventListener("click", function () {
                const request = getRequestFromElement(button);

                if (!request) {
                    return;
                }

                sendMessage(request);
            });
        });

        const launcher = document.getElementById("copilotLauncher");
        const closeButton = document.getElementById("copilotCloseButton");
        const expandButton = document.getElementById("copilotExpandButton");

        if (launcher) {
            launcher.addEventListener("click", openCopilot);
        }

        if (closeButton) {
            closeButton.addEventListener("click", closeCopilot);
        }

        if (expandButton) {
            expandButton.addEventListener("click", toggleExpanded);
        }

        if (!hasRequiredChatElements()) {
            console.warn("Operational Copilot: chat interface loaded with missing nodes.");
            return;
        }

        submitButton.addEventListener("click", function () {
            sendMessage();
        });

        if (clearButton) {
            clearButton.addEventListener("click", function () {
                clearConversation();
                conversationHistory = [];
                clearStoredRequestHistory();
                clearStoredMessages();
                updateHistoryList();
            });
        }

        messageInput.addEventListener("input", autoResizeTextarea);

        messageInput.addEventListener("keydown", function (event) {
            if (event.key !== "Enter") {
                return;
            }

            if (event.shiftKey) {
                return;
            }

            event.preventDefault();
            sendMessage();
        });

        localizeCopilotStaticInterface();
        conversationHistory = readStoredRequestHistory();
        restoreStoredConversation();
        updateHistoryList();
        autoResizeTextarea();
    });
})();