from pathlib import Path
import polib


BASE_DIR = Path(__file__).resolve().parent.parent

PO_FILES = {
    "fr": BASE_DIR / "locale" / "fr" / "LC_MESSAGES" / "django.po",
    "ru": BASE_DIR / "locale" / "ru" / "LC_MESSAGES" / "django.po",
}


FR = {
    "Operational Intelligence": "Intelligence opérationnelle",
    "Monitor flight activity, disruptions, route exposure and data sources from one operations view.": "Surveillez l’activité des vols, les perturbations, l’exposition des routes et les sources de données depuis une seule vue opérationnelle.",
    "Operations view": "Vue opérationnelle",
    "Current flight performance overview": "Vue d’ensemble de la performance actuelle des vols",
    "Follow the main operating picture from the flight database: active movement, delayed and cancelled flights, busiest corridors, airline activity and data source coverage.": "Suivez l’image opérationnelle principale depuis la base des vols : mouvement actif, vols retardés et annulés, couloirs les plus utilisés, activité des compagnies et couverture des sources de données.",
    "Open charts": "Ouvrir les graphiques",
    "View reports": "Voir les rapports",
    "Current status": "Statut actuel",
    "Flight records visible in the current operational dataset.": "Enregistrements de vols visibles dans les données opérationnelles actuelles.",
    "%(rate)s% of records are currently in active flow.": "%(rate)s%% des enregistrements sont actuellement dans un flux actif.",
    "%(rate)s% of the current dataset.": "%(rate)s%% des données actuelles.",
    "Operations briefing": "Briefing opérationnel",
    "What needs attention first": "Ce qui demande l’attention en premier",
    "This short briefing turns the current data into a readable operational summary. It is meant for supervision, reporting and decision support.": "Ce court briefing transforme les données actuelles en résumé opérationnel lisible. Il sert à la supervision, au reporting et à l’aide à la décision.",
    "Priority corridor": "Couloir prioritaire",
    "Route with the highest concentration inside the current flight dataset.": "Route avec la plus forte concentration dans les données de vols actuelles.",
    "Operations are stable. Maintain standard supervision and data validation.": "Les opérations sont stables. Maintenez une supervision standard et la validation des données.",
    "Key signals": "Signaux clés",
    "Current highlights": "Points importants actuels",
    "Operational score": "Score opérationnel",
    "Dominant state": "État dominant",
    "Main status in the visible dataset.": "Statut principal dans les données visibles.",
    "Most active airline": "Compagnie la plus active",
    "Airline with the highest visible activity.": "Compagnie avec la plus forte activité visible.",
    "Source balance": "Équilibre des sources",
    "API %(api)s / Local %(local)s": "API %(api)s / Local %(local)s",
    "External data and local records in the platform.": "Données externes et enregistrements locaux dans la plateforme.",
    "Status distribution": "Distribution des statuts",
    "Flight states": "États des vols",
    "Breakdown of the visible records by operational state.": "Répartition des enregistrements visibles par état opérationnel.",
    "Route exposure": "Exposition des routes",
    "Busiest corridors": "Couloirs les plus actifs",
    "Top route concentration in the current data view.": "Plus forte concentration de routes dans la vue de données actuelle.",
    "No route data available.": "Aucune donnée de route disponible.",

    "Operational Copilot": "Copilot opérationnel",
    "A cross-platform assistance layer available across the private operations workspace.": "Une couche d’assistance disponible dans tout l’espace privé des opérations.",
    "FlightLogos Assist": "Assistant FlightLogos",
    "Operational Copilot is not a separate workspace": "Le Copilot opérationnel n’est pas un espace séparé",
    "The Copilot works as a floating assistant available across the private platform. Use it while viewing operations, monitoring, flight records, route exposure, analytics or data synchronization.": "Le Copilot fonctionne comme un assistant flottant disponible dans toute la plateforme privée. Utilisez-le pendant la consultation des opérations, du monitoring, des fiches de vol, de l’exposition des routes, de l’analytics ou de la synchronisation des données.",
    "Open the assistant": "Ouvrir l’assistant",
    "Start a quick operational question from this page.": "Lancer une question opérationnelle rapide depuis cette page.",
    "Ask about operations": "Poser une question sur les opérations",
    "Read delays, cancellations, route pressure and KPIs.": "Lire les retards, les annulations, la pression des routes et les KPI.",
    "Go to Operations Center": "Aller au centre des opérations",
    "Return to the main operational workspace.": "Retourner à l’espace opérationnel principal.",
    "Open Intelligence": "Ouvrir l’intelligence",
    "Review reports, charts, routes and data quality.": "Examiner les rapports, graphiques, routes et la qualité des données.",
}


RU = {
    "Operational Intelligence": "Операционная аналитика",
    "Monitor flight activity, disruptions, route exposure and data sources from one operations view.": "Контролируйте активность рейсов, сбои, маршруты и источники данных из одной операционной панели.",
    "Operations view": "Операционная панель",
    "Current flight performance overview": "Обзор текущей эффективности рейсов",
    "Follow the main operating picture from the flight database: active movement, delayed and cancelled flights, busiest corridors, airline activity and data source coverage.": "Отслеживайте основную операционную картину из базы рейсов: активное движение, задержанные и отменённые рейсы, самые загруженные коридоры, активность авиакомпаний и покрытие источников данных.",
    "Open charts": "Открыть графики",
    "View reports": "Посмотреть отчёты",
    "Current status": "Текущий статус",
    "Flight records visible in the current operational dataset.": "Записи рейсов, видимые в текущем операционном наборе данных.",
    "%(rate)s% of records are currently in active flow.": "%(rate)s%% записей сейчас находятся в активном потоке.",
    "%(rate)s% of the current dataset.": "%(rate)s%% текущего набора данных.",
    "Operations briefing": "Операционный брифинг",
    "What needs attention first": "Что требует внимания в первую очередь",
    "This short briefing turns the current data into a readable operational summary. It is meant for supervision, reporting and decision support.": "Этот краткий брифинг превращает текущие данные в понятную операционную сводку. Он предназначен для контроля, отчётности и поддержки решений.",
    "Priority corridor": "Приоритетный коридор",
    "Route with the highest concentration inside the current flight dataset.": "Маршрут с самой высокой концентрацией в текущем наборе данных рейсов.",
    "Operations are stable. Maintain standard supervision and data validation.": "Операции стабильны. Поддерживайте стандартный контроль и проверку данных.",
    "Key signals": "Ключевые сигналы",
    "Current highlights": "Текущие основные показатели",
    "Operational score": "Операционный балл",
    "Dominant state": "Доминирующее состояние",
    "Main status in the visible dataset.": "Основной статус в видимом наборе данных.",
    "Most active airline": "Самая активная авиакомпания",
    "Airline with the highest visible activity.": "Авиакомпания с самой высокой видимой активностью.",
    "Source balance": "Баланс источников",
    "API %(api)s / Local %(local)s": "API %(api)s / Локально %(local)s",
    "External data and local records in the platform.": "Внешние данные и локальные записи в платформе.",
    "Status distribution": "Распределение статусов",
    "Flight states": "Состояния рейсов",
    "Breakdown of the visible records by operational state.": "Разделение видимых записей по операционным состояниям.",
    "Route exposure": "Экспозиция маршрутов",
    "Busiest corridors": "Самые загруженные коридоры",
    "Top route concentration in the current data view.": "Наибольшая концентрация маршрутов в текущем представлении данных.",
    "No route data available.": "Данные маршрутов недоступны.",

    "Operational Copilot": "Операционный Copilot",
    "A cross-platform assistance layer available across the private operations workspace.": "Слой помощи, доступный во всей закрытой операционной рабочей зоне.",
    "FlightLogos Assist": "Ассистент FlightLogos",
    "Operational Copilot is not a separate workspace": "Операционный Copilot не является отдельным рабочим пространством",
    "The Copilot works as a floating assistant available across the private platform. Use it while viewing operations, monitoring, flight records, route exposure, analytics or data synchronization.": "Copilot работает как плавающий ассистент, доступный по всей закрытой платформе. Используйте его при просмотре операций, мониторинга, записей рейсов, маршрутов, аналитики или синхронизации данных.",
    "Open the assistant": "Открыть ассистента",
    "Start a quick operational question from this page.": "Задать быстрый операционный вопрос с этой страницы.",
    "Ask about operations": "Спросить об операциях",
    "Read delays, cancellations, route pressure and KPIs.": "Анализировать задержки, отмены, давление маршрутов и KPI.",
    "Go to Operations Center": "Перейти в центр операций",
    "Return to the main operational workspace.": "Вернуться в основную операционную рабочую зону.",
    "Open Intelligence": "Открыть аналитику",
    "Review reports, charts, routes and data quality.": "Просмотреть отчёты, графики, маршруты и качество данных.",
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