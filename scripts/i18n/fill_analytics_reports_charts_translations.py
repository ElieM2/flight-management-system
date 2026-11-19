from pathlib import Path
import polib


BASE_DIR = Path(__file__).resolve().parent.parent

PO_FILES = {
    "fr": BASE_DIR / "locale" / "fr" / "LC_MESSAGES" / "django.po",
    "ru": BASE_DIR / "locale" / "ru" / "LC_MESSAGES" / "django.po",
}


FR = {
    "Charts": "Graphiques",
    "Reports": "Rapports",
    "Operational Intelligence": "Intelligence opérationnelle",

    "Dedicated graphical board for operational distribution, airline exposure, routes, and data sources.": "Tableau graphique dédié à la distribution opérationnelle, à l’exposition des compagnies, aux routes et aux sources de données.",
    "Charts | Operational Intelligence": "Graphiques | Intelligence opérationnelle",
    "Graphical analysis board.": "Tableau d’analyse graphique.",
    "This page isolates the graphs so visual interpretation stays clean. It is closer to a real operational analytics screen.": "Cette page isole les graphiques afin que l’interprétation visuelle reste claire. Elle se rapproche d’un vrai écran d’analytics opérationnel.",
    "Operational score": "Score opérationnel",
    "Status pressure": "Pression des statuts",
    "Operational states distribution": "Distribution des états opérationnels",
    "Scheduled, active, landed, delayed and cancelled records.": "Enregistrements prévus, actifs, atterris, retardés et annulés.",
    "Airline exposure": "Exposition des compagnies",
    "Highest operational load": "Charge opérationnelle la plus élevée",
    "Airlines carrying the largest number of records.": "Compagnies avec le plus grand nombre d’enregistrements.",
    "Route concentration": "Concentration des routes",
    "Priority corridors": "Couloirs prioritaires",
    "Routes with the strongest visible concentration.": "Routes avec la plus forte concentration visible.",
    "Source balance": "Équilibre des sources",
    "API and local data": "Données API et locales",
    "Hybrid data composition used by the platform.": "Composition hybride des données utilisée par la plateforme.",
    "Disruption mix": "Composition des perturbations",
    "Delay and cancellation share": "Part des retards et annulations",
    "Simple view separating delayed, cancelled and other visible records.": "Vue simple séparant les vols retardés, annulés et les autres enregistrements visibles.",
    "Tracked flights": "Vols suivis",

    "Filtered reports by airline, airport, route, status, and data source.": "Rapports filtrés par compagnie, aéroport, route, statut et source de données.",
    "Readable operational reports.": "Rapports opérationnels lisibles.",
    "Use this page for structured tables. It is intentionally separated from charts so the report layer stays calm, searchable, and easy to defend.": "Utilisez cette page pour les tableaux structurés. Elle est volontairement séparée des graphiques afin que la couche rapport reste claire, recherchable et facile à défendre.",
    "Current posture": "Posture actuelle",
    "Filters": "Filtres",
    "Refine report view": "Affiner la vue du rapport",
    "Filter records by status, source, or airline.": "Filtrer les enregistrements par statut, source ou compagnie.",
    "Status": "Statut",
    "All statuses": "Tous les statuts",
    "Source": "Source",
    "All sources": "Toutes les sources",
    "API synchronized": "Synchronisé API",
    "Local records": "Enregistrements locaux",
    "Airline": "Compagnie",
    "All airlines": "Toutes les compagnies",
    "Apply filters": "Appliquer les filtres",
    "Reset": "Réinitialiser",
    "Filtered view active. Showing %(total)s records from %(base_total)s total registered flights.": "Vue filtrée active. Affichage de %(total)s enregistrements sur %(base_total)s vols enregistrés au total.",
    "Visible records": "Enregistrements visibles",
    "Records matching the current report.": "Enregistrements correspondant au rapport actuel.",
    "%(rate)s% active flow.": "%(rate)s%% de flux actif.",
    "%(rate)s% delayed.": "%(rate)s%% retardés.",
    "%(rate)s% cancelled.": "%(rate)s%% annulés.",
    "By airline": "Par compagnie",
    "Airline activity report": "Rapport d’activité par compagnie",
    "Operational load grouped by airline.": "Charge opérationnelle groupée par compagnie.",
    "Flights": "Vols",
    "Share": "Part",
    "No airline report available.": "Aucun rapport par compagnie disponible.",
    "By origin airport": "Par aéroport d’origine",
    "Departure concentration": "Concentration des départs",
    "Airports generating the strongest departure activity.": "Aéroports générant la plus forte activité de départ.",
    "Airport": "Aéroport",
    "Name": "Nom",
    "No origin airport report available.": "Aucun rapport d’aéroport d’origine disponible.",
    "By destination airport": "Par aéroport de destination",
    "Arrival concentration": "Concentration des arrivées",
    "Airports receiving the strongest destination activity.": "Aéroports recevant la plus forte activité de destination.",
    "No destination airport report available.": "Aucun rapport d’aéroport de destination disponible.",
    "Operational feed": "Flux opérationnel",
    "Recent flight records": "Enregistrements récents des vols",
    "Latest records captured by the system across operations and data sources.": "Derniers enregistrements capturés par le système à travers les opérations et les sources de données.",
    "Flight": "Vol",
    "Route": "Route",
    "Operational state": "État opérationnel",
    "Unknown airline": "Compagnie inconnue",
    "Unknown": "Inconnu",
    "Local": "Local",
    "No recent operational records available.": "Aucun enregistrement opérationnel récent disponible.",
}


RU = {
    "Charts": "Графики",
    "Reports": "Отчёты",
    "Operational Intelligence": "Операционная аналитика",

    "Dedicated graphical board for operational distribution, airline exposure, routes, and data sources.": "Графическая панель для распределения операций, нагрузки авиакомпаний, маршрутов и источников данных.",
    "Charts | Operational Intelligence": "Графики | Операционная аналитика",
    "Graphical analysis board.": "Панель графического анализа.",
    "This page isolates the graphs so visual interpretation stays clean. It is closer to a real operational analytics screen.": "Эта страница отделяет графики, чтобы визуальная интерпретация оставалась понятной. Она ближе к настоящему экрану операционной аналитики.",
    "Operational score": "Операционный балл",
    "Status pressure": "Давление статусов",
    "Operational states distribution": "Распределение операционных состояний",
    "Scheduled, active, landed, delayed and cancelled records.": "Запланированные, активные, завершённые, задержанные и отменённые записи.",
    "Airline exposure": "Нагрузка авиакомпаний",
    "Highest operational load": "Наибольшая операционная нагрузка",
    "Airlines carrying the largest number of records.": "Авиакомпании с наибольшим количеством записей.",
    "Route concentration": "Концентрация маршрутов",
    "Priority corridors": "Приоритетные коридоры",
    "Routes with the strongest visible concentration.": "Маршруты с самой высокой видимой концентрацией.",
    "Source balance": "Баланс источников",
    "API and local data": "API и локальные данные",
    "Hybrid data composition used by the platform.": "Гибридный состав данных, используемый платформой.",
    "Disruption mix": "Состав сбоев",
    "Delay and cancellation share": "Доля задержек и отмен",
    "Simple view separating delayed, cancelled and other visible records.": "Простое представление, разделяющее задержанные, отменённые и другие видимые записи.",
    "Tracked flights": "Отслеживаемые рейсы",

    "Filtered reports by airline, airport, route, status, and data source.": "Отчёты с фильтрацией по авиакомпании, аэропорту, маршруту, статусу и источнику данных.",
    "Readable operational reports.": "Понятные операционные отчёты.",
    "Use this page for structured tables. It is intentionally separated from charts so the report layer stays calm, searchable, and easy to defend.": "Используйте эту страницу для структурированных таблиц. Она специально отделена от графиков, чтобы слой отчётов оставался спокойным, удобным для поиска и понятным на защите.",
    "Current posture": "Текущая позиция",
    "Filters": "Фильтры",
    "Refine report view": "Уточнить вид отчёта",
    "Filter records by status, source, or airline.": "Фильтруйте записи по статусу, источнику или авиакомпании.",
    "Status": "Статус",
    "All statuses": "Все статусы",
    "Source": "Источник",
    "All sources": "Все источники",
    "API synchronized": "Синхронизировано API",
    "Local records": "Локальные записи",
    "Airline": "Авиакомпания",
    "All airlines": "Все авиакомпании",
    "Apply filters": "Применить фильтры",
    "Reset": "Сбросить",
    "Filtered view active. Showing %(total)s records from %(base_total)s total registered flights.": "Активен фильтрованный вид. Показано %(total)s записей из %(base_total)s зарегистрированных рейсов.",
    "Visible records": "Видимые записи",
    "Records matching the current report.": "Записи, соответствующие текущему отчёту.",
    "%(rate)s% active flow.": "%(rate)s%% активного потока.",
    "%(rate)s% delayed.": "%(rate)s%% задержанных.",
    "%(rate)s% cancelled.": "%(rate)s%% отменённых.",
    "By airline": "По авиакомпании",
    "Airline activity report": "Отчёт активности авиакомпаний",
    "Operational load grouped by airline.": "Операционная нагрузка, сгруппированная по авиакомпаниям.",
    "Flights": "Рейсы",
    "Share": "Доля",
    "No airline report available.": "Отчёт по авиакомпаниям недоступен.",
    "By origin airport": "По аэропорту вылета",
    "Departure concentration": "Концентрация вылетов",
    "Airports generating the strongest departure activity.": "Аэропорты с самой высокой активностью вылетов.",
    "Airport": "Аэропорт",
    "Name": "Название",
    "No origin airport report available.": "Отчёт по аэропортам вылета недоступен.",
    "By destination airport": "По аэропорту прибытия",
    "Arrival concentration": "Концентрация прибытий",
    "Airports receiving the strongest destination activity.": "Аэропорты с самой высокой активностью прибытий.",
    "No destination airport report available.": "Отчёт по аэропортам прибытия недоступен.",
    "Operational feed": "Операционный поток",
    "Recent flight records": "Последние записи рейсов",
    "Latest records captured by the system across operations and data sources.": "Последние записи, собранные системой из операций и источников данных.",
    "Flight": "Рейс",
    "Route": "Маршрут",
    "Operational state": "Операционное состояние",
    "Unknown airline": "Неизвестная авиакомпания",
    "Unknown": "Неизвестно",
    "Local": "Локально",
    "No recent operational records available.": "Последние операционные записи отсутствуют.",
}


def patch_po(path, translations, language):
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    po = polib.pofile(str(path))
    updated = 0
    created = 0

    for msgid, msgstr in translations.items():
        entry = po.find(msgid)

        if entry:
            if entry.msgstr != msgstr:
                entry.msgstr = msgstr
                updated += 1

            if "fuzzy" in entry.flags:
                entry.flags.remove("fuzzy")
        else:
            po.append(polib.POEntry(msgid=msgid, msgstr=msgstr))
            created += 1

    po.save(str(path))
    print(f"{language}: updated={updated}, created={created}, file={path}")


def main():
    patch_po(PO_FILES["fr"], FR, "French")
    patch_po(PO_FILES["ru"], RU, "Russian")


if __name__ == "__main__":
    main()