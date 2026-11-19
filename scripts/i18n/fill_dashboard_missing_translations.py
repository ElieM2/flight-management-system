from pathlib import Path
import polib


BASE_DIR = Path(__file__).resolve().parent.parent

PO_FILES = {
    "fr": BASE_DIR / "locale" / "fr" / "LC_MESSAGES" / "django.po",
    "ru": BASE_DIR / "locale" / "ru" / "LC_MESSAGES" / "django.po",
}


FR = {
    "Operations Center": "Centre des opérations",
    "Private Operations": "Opérations privées",
    "Private aviation workspace for flight supervision, disruption review, route visibility and operational reporting.": "Espace privé pour la supervision des vols, l’analyse des perturbations, la visibilité des routes et les rapports opérationnels.",

    "FlightLogos operations network": "Réseau opérationnel FlightLogos",
    "Critical Supervision": "Supervision critique",
    "Disruption pressure is high. Review cancellations, delayed flights and affected routes first.": "La pression de perturbation est élevée. Vérifiez d’abord les annulations, les vols retardés et les routes affectées.",

    "Primary operational focus": "Priorité opérationnelle",
    "Cancelled flights and recovery actions": "Vols annulés et actions de récupération",
    "Start with the highest pressure signal, then move to control, map visibility, irregular operations or intelligence reports.": "Commencez par le signal le plus sensible, puis passez au contrôle, à la carte, aux opérations irrégulières ou aux rapports d’intelligence.",
    "Open control": "Ouvrir le contrôle",
    "Irregular ops": "Ops irrégulières",
    "Flight map": "Carte des vols",
    "Intelligence": "Intelligence",

    "Total flights": "Total des vols",
    "Records in platform": "Enregistrements dans la plateforme",
    "Active": "Actif",
    "%(rate)s% active share": "%(rate)s%% de part active",
    "Critical": "Critique",
    "Delayed + cancelled": "Retardés + annulés",
    "Main state": "État principal",
    "Dominant status now": "Statut dominant actuel",

    "Active movement": "Mouvement actif",
    "All flight records currently stored in the platform.": "Tous les enregistrements de vols actuellement stockés dans la plateforme.",
    "%(rate)s% of the current flight dataset.": "%(rate)s%% de l’ensemble actuel des vols.",
    "In air": "En vol",
    "Flights currently marked as airborne.": "Vols actuellement marqués comme en vol.",
    "Delayed": "Retardé",
    "%(rate)s% delay rate.": "%(rate)s%% de taux de retard.",
    "Cancelled": "Annulé",
    "%(rate)s% cancellation rate.": "%(rate)s%% de taux d’annulation.",
    "Stable": "Stable",
    "Scheduled and landed records.": "Enregistrements prévus et atterris.",

    "Attention board": "Tableau d’attention",
    "What should be checked first": "Ce qui doit être vérifié en premier",
    "Short operational reading generated from the current flight dataset.": "Lecture opérationnelle courte générée à partir des données actuelles de vols.",
    "%(count)s cancelled flight needs recovery review.": "%(count)s vol annulé nécessite une revue de récupération.",
    "%(count)s cancelled flights need recovery review.": "%(count)s vols annulés nécessitent une revue de récupération.",
    "%(count)s delayed flight is adding pressure to the operating picture.": "%(count)s vol retardé ajoute une pression à l’image opérationnelle.",
    "%(count)s delayed flights are adding pressure to the operating picture.": "%(count)s vols retardés ajoutent une pression à l’image opérationnelle.",
    "%(airline)s is the busiest airline in the current dataset.": "%(airline)s est la compagnie la plus active dans les données actuelles.",
    "Most monitored route: %(route)s.": "Route la plus surveillée : %(route)s.",

    "Data picture": "Image des données",
    "API-led dataset": "Données dominées par l’API",
    "External synchronized records currently lead the operational dataset.": "Les enregistrements synchronisés externes dominent actuellement les données opérationnelles.",
    "API flights": "Vols API",
    "Local flights": "Vols locaux",
    "%(rate)s% of total records.": "%(rate)s%% du total des enregistrements.",
    "Main route": "Route principale",
    "Most represented corridor.": "Couloir le plus représenté.",
    "Critical rate": "Taux critique",
    "Delayed and cancelled share.": "Part des vols retardés et annulés.",

    "Workspace routing": "Orientation de l’espace de travail",
    "Open the right operational layer": "Ouvrir la bonne couche opérationnelle",
    "Each module has a clear role inside the private aviation workspace.": "Chaque module a un rôle clair dans l’espace privé aéronautique.",
    "Start supervision": "Démarrer la supervision",

    "Copilot": "Copilot",
    "Assistant": "Assistant",
    "Ask Copilot": "Demander au Copilot",
}


RU = {
    "Operations Center": "Центр операций",
    "Private Operations": "Закрытая зона",
    "Private aviation workspace for flight supervision, disruption review, route visibility and operational reporting.": "Закрытая рабочая зона для контроля рейсов, анализа сбоев, видимости маршрутов и операционной отчётности.",

    "FlightLogos operations network": "Операционная сеть FlightLogos",
    "Critical Supervision": "Критический контроль",
    "Disruption pressure is high. Review cancellations, delayed flights and affected routes first.": "Давление сбоев высокое. Сначала проверьте отмены, задержанные рейсы и затронутые маршруты.",

    "Primary operational focus": "Главный операционный фокус",
    "Cancelled flights and recovery actions": "Отменённые рейсы и действия восстановления",
    "Start with the highest pressure signal, then move to control, map visibility, irregular operations or intelligence reports.": "Начните с самого сильного сигнала нагрузки, затем переходите к контролю, карте, нештатным операциям или аналитическим отчётам.",
    "Open control": "Открыть контроль",
    "Irregular ops": "Нештатные операции",
    "Flight map": "Карта рейсов",
    "Intelligence": "Аналитика",

    "Total flights": "Всего рейсов",
    "Records in platform": "Записи в платформе",
    "Active": "Активно",
    "%(rate)s% active share": "%(rate)s%% активная доля",
    "Critical": "Критично",
    "Delayed + cancelled": "Задержаны + отменены",
    "Main state": "Основное состояние",
    "Dominant status now": "Текущий доминирующий статус",

    "Active movement": "Активное движение",
    "All flight records currently stored in the platform.": "Все записи рейсов, которые сейчас хранятся в платформе.",
    "%(rate)s% of the current flight dataset.": "%(rate)s%% текущего набора рейсов.",
    "In air": "В полёте",
    "Flights currently marked as airborne.": "Рейсы, отмеченные как находящиеся в полёте.",
    "Delayed": "Задержан",
    "%(rate)s% delay rate.": "%(rate)s%% уровень задержек.",
    "Cancelled": "Отменён",
    "%(rate)s% cancellation rate.": "%(rate)s%% уровень отмен.",
    "Stable": "Стабильно",
    "Scheduled and landed records.": "Запланированные и завершённые записи.",

    "Attention board": "Панель внимания",
    "What should be checked first": "Что проверить первым",
    "Short operational reading generated from the current flight dataset.": "Краткая операционная сводка, созданная по текущим данным рейсов.",
    "%(count)s cancelled flight needs recovery review.": "%(count)s отменённый рейс требует проверки восстановления.",
    "%(count)s cancelled flights need recovery review.": "%(count)s отменённых рейсов требуют проверки восстановления.",
    "%(count)s delayed flight is adding pressure to the operating picture.": "%(count)s задержанный рейс добавляет нагрузку к операционной картине.",
    "%(count)s delayed flights are adding pressure to the operating picture.": "%(count)s задержанных рейсов добавляют нагрузку к операционной картине.",
    "%(airline)s is the busiest airline in the current dataset.": "%(airline)s — самая активная авиакомпания в текущем наборе данных.",
    "Most monitored route: %(route)s.": "Самый контролируемый маршрут: %(route)s.",

    "Data picture": "Картина данных",
    "API-led dataset": "Набор данных с преобладанием API",
    "External synchronized records currently lead the operational dataset.": "Внешние синхронизированные записи сейчас преобладают в операционном наборе данных.",
    "API flights": "Рейсы API",
    "Local flights": "Локальные рейсы",
    "%(rate)s% of total records.": "%(rate)s%% всех записей.",
    "Main route": "Основной маршрут",
    "Most represented corridor.": "Наиболее представленный коридор.",
    "Critical rate": "Критический показатель",
    "Delayed and cancelled share.": "Доля задержанных и отменённых рейсов.",

    "Workspace routing": "Навигация рабочего пространства",
    "Open the right operational layer": "Открыть нужный операционный слой",
    "Each module has a clear role inside the private aviation workspace.": "У каждого модуля есть чёткая роль в закрытой авиационной рабочей зоне.",
    "Start supervision": "Начать контроль",

    "Copilot": "Copilot",
    "Assistant": "Помощник",
    "Ask Copilot": "Спросить Copilot",
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