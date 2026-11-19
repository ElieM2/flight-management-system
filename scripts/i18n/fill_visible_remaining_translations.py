from pathlib import Path
import re
import polib


BASE_DIR = Path(__file__).resolve().parent.parent

PO_FILES = {
    "fr": BASE_DIR / "locale" / "fr" / "LC_MESSAGES" / "django.po",
    "ru": BASE_DIR / "locale" / "ru" / "LC_MESSAGES" / "django.po",
}


FR = {
    # Global / states
    "Success": "Succès",
    "Failed": "Échec",
    "Pending": "En attente",
    "Healthy": "Stable",
    "Stable history": "Historique stable",
    "Unstable history": "Historique instable",
    "No history": "Aucun historique",
    "Current status": "Statut actuel",
    "Latest run": "Dernière exécution",
    "Latest duration": "Dernière durée",
    "Provider status": "État du fournisseur",

    # Sync page
    "Data Sync Hub": "Centre de synchronisation des données",
    "External flight data synchronization, provider logs, import status and local database updates.": "Synchronisation externe des données de vol, journaux fournisseur, état d’importation et mises à jour de la base locale.",
    "External data feed": "Flux de données externe",
    "Flight data synchronization": "Synchronisation des données de vol",
    "Import external flight records, update the local database, and keep a clear trace of provider runs, created records, updated records and synchronization errors.": "Importez des enregistrements de vols externes, mettez à jour la base locale et gardez une trace claire des exécutions fournisseur, des enregistrements créés, mis à jour et des erreurs de synchronisation.",
    "Provider": "Fournisseur",
    "Total runs": "Exécutions totales",
    "Success rate": "Taux de réussite",
    "Records received": "Enregistrements reçus",
    "Recent synchronization history contains a high failure rate.": "L’historique récent de synchronisation contient un taux d’échec élevé.",
    "Recent synchronization history is stable.": "L’historique récent de synchronisation est stable.",
    "No synchronization run has been recorded yet.": "Aucune exécution de synchronisation n’a encore été enregistrée.",
    "Measured from provider request start to recorded completion.": "Mesuré entre le début de la requête fournisseur et la fin enregistrée.",
    "Run sync": "Lancer la synchronisation",
    "Run synchronization": "Lancer la synchronisation",
    "Hybrid data": "Données hybrides",
    "History": "Historique",
    "Logs": "Journaux",
    "Successful runs": "Exécutions réussies",
    "Provider executions completed successfully.": "Exécutions fournisseur terminées avec succès.",
    "Failed runs": "Exécutions échouées",
    "Runs that ended with provider, access or network errors.": "Exécutions terminées avec des erreurs fournisseur, d’accès ou de réseau.",
    "Created records": "Enregistrements créés",
    "Updated records": "Enregistrements mis à jour",
    "Existing records refreshed by synchronization.": "Enregistrements existants actualisés par la synchronisation.",
    "Latest synchronization result": "Résultat de la dernière synchronisation",
    "Most recent provider execution recorded by the platform.": "Dernière exécution fournisseur enregistrée par la plateforme.",
    "Received": "Reçus",
    "Created": "Créés",
    "Updated": "Mis à jour",
    "Run a focused import when demonstrating the API layer to avoid unnecessary provider load.": "Lancez un import ciblé pendant la démonstration de la couche API afin d’éviter une charge inutile du fournisseur.",
    "After every run, check received, created and updated records before opening reports.": "Après chaque exécution, vérifiez les enregistrements reçus, créés et mis à jour avant d’ouvrir les rapports.",
    "Failed runs remain visible in the log so provider errors can be explained and traced.": "Les exécutions échouées restent visibles dans le journal afin d’expliquer et tracer les erreurs fournisseur.",
    "Synchronization trace": "Trace de synchronisation",
    "Provider execution history, ingestion volume and technical messages.": "Historique d’exécution fournisseur, volume d’ingestion et messages techniques.",
    "No synchronization logs available.": "Aucun journal de synchronisation disponible.",
    "Failed run — %(provider)s / %(sync_type)s on %(started)s.": "Exécution échouée — %(provider)s / %(sync_type)s le %(started)s.",

    # Analytics
    "Operational Intelligence": "Intelligence opérationnelle",
    "Performance, routes, reports and source quality": "Performance, routes, rapports et qualité des sources",
    "Critical Supervision": "Supervision critique",
    "Elevated Supervision": "Supervision renforcée",
    "Stable Operations": "Opérations stables",
    "Current flight performance overview": "Vue d’ensemble de la performance actuelle des vols",
    "Disruption pressure is visible. Prioritize cancelled flights, delayed operations, and the busiest corridor before expanding the analysis.": "Une pression de perturbation est visible. Priorisez les vols annulés, les opérations retardées et le couloir le plus chargé avant d’élargir l’analyse.",
    "Operations remain readable, but active disruption pockets require targeted attention.": "Les opérations restent lisibles, mais certains foyers de perturbation exigent une attention ciblée.",
    "The visible operational picture is stable. Continue standard supervision and data validation.": "L’image opérationnelle visible est stable. Continuez la supervision normale et la validation des données.",
    "%(rate)s%% of records are currently in active flow.": "%(rate)s%% des enregistrements sont actuellement en flux actif.",
    "%(rate)s%% of the current dataset.": "%(rate)s%% du jeu de données actuel.",
    "%(rate)s%% active flow.": "%(rate)s%% en flux actif.",
    "%(rate)s%% active share": "%(rate)s%% de part active",
    "%(rate)s%% of the current flight dataset.": "%(rate)s%% du jeu de données de vols actuel.",
    "%(rate)s%% delay rate.": "%(rate)s%% de taux de retard.",
    "%(rate)s%% cancellation rate.": "%(rate)s%% de taux d’annulation.",
    "%(rate)s%% of total records.": "%(rate)s%% du total des enregistrements.",
    "Priority corridor to watch: %(route)s.": "Couloir prioritaire à surveiller : %(route)s.",
    "Review cancelled flights and validate recovery actions before presenting the report.": "Revoyez les vols annulés et validez les actions de récupération avant de présenter le rapport.",
    "Track delayed flights and compare them with route concentration and airport activity.": "Suivez les vols retardés et comparez-les avec la concentration des routes et l’activité des aéroports.",
    "External synchronized data is dominant. Confirm API consistency and explain this as a hybrid data model.": "Les données synchronisées externes dominent. Confirmez la cohérence API et présentez cela comme un modèle de données hybride.",
    "No flight records are visible in this report. Check filters or synchronize operational data.": "Aucun enregistrement de vol n’est visible dans ce rapport. Vérifiez les filtres ou synchronisez les données opérationnelles.",

    # Map
    "All traffic": "Tout le trafic",
    "Traffic Surface": "Surface du trafic",
    "Live map view of operational traffic and exposed services.": "Vue cartographique du trafic opérationnel et des services exposés.",
    "Confirmed": "Confirmé",
    "Associated": "Associé",
    "Low": "Faible",
    "Simulated": "Simulé",
    "Selected flight": "Vol sélectionné",
    "Standby": "En attente",
    "Ready for inspection": "Prêt pour inspection",
    "Operational visibility": "Visibilité opérationnelle",
    "Clear reading": "Lecture claire",
    "Use the map to identify active services, delayed traffic and flights that deserve closer attention.": "Utilisez la carte pour identifier les services actifs, le trafic retardé et les vols nécessitant une attention rapprochée.",
    "The panel keeps only the information needed for a fast operational review.": "Le panneau conserve uniquement les informations nécessaires à une revue opérationnelle rapide.",
    "Start with a delayed flight, a selected route, or a service flagged in the visible traffic.": "Commencez par un vol retardé, une route sélectionnée ou un service signalé dans le trafic visible.",
    "CRISIS": "CRISE",
    "%(cancelled)s cancelled · %(delayed)s delayed · %(high_risk)s high risk.": "%(cancelled)s annulé(s) · %(delayed)s retardé(s) · %(high_risk)s à haut risque.",
}


RU = {
    # Global / states
    "Success": "Успешно",
    "Failed": "Ошибка",
    "Pending": "Ожидание",
    "Healthy": "Стабильно",
    "Stable history": "Стабильная история",
    "Unstable history": "Нестабильная история",
    "No history": "Нет истории",
    "Current status": "Текущий статус",
    "Latest run": "Последний запуск",
    "Latest duration": "Последняя длительность",
    "Provider status": "Статус поставщика",

    # Sync page
    "Data Sync Hub": "Центр синхронизации данных",
    "External flight data synchronization, provider logs, import status and local database updates.": "Синхронизация внешних данных о рейсах, журналы поставщика, статус импорта и обновления локальной базы данных.",
    "External data feed": "Внешний поток данных",
    "Flight data synchronization": "Синхронизация данных о рейсах",
    "Import external flight records, update the local database, and keep a clear trace of provider runs, created records, updated records and synchronization errors.": "Импортируйте внешние записи о рейсах, обновляйте локальную базу данных и сохраняйте понятную историю запусков поставщика, созданных записей, обновлений и ошибок синхронизации.",
    "Provider": "Поставщик",
    "Total runs": "Всего запусков",
    "Success rate": "Процент успеха",
    "Records received": "Получено записей",
    "Recent synchronization history contains a high failure rate.": "В последней истории синхронизации высокий процент ошибок.",
    "Recent synchronization history is stable.": "Последняя история синхронизации стабильна.",
    "No synchronization run has been recorded yet.": "Запуск синхронизации ещё не зарегистрирован.",
    "Measured from provider request start to recorded completion.": "Измеряется от начала запроса к поставщику до зафиксированного завершения.",
    "Run sync": "Запустить синхронизацию",
    "Run synchronization": "Запустить синхронизацию",
    "Hybrid data": "Гибридные данные",
    "History": "История",
    "Logs": "Журналы",
    "Successful runs": "Успешные запуски",
    "Provider executions completed successfully.": "Запуски поставщика, завершённые успешно.",
    "Failed runs": "Неудачные запуски",
    "Runs that ended with provider, access or network errors.": "Запуски, завершившиеся ошибками поставщика, доступа или сети.",
    "Created records": "Созданные записи",
    "Updated records": "Обновлённые записи",
    "Existing records refreshed by synchronization.": "Существующие записи, обновлённые синхронизацией.",
    "Latest synchronization result": "Результат последней синхронизации",
    "Most recent provider execution recorded by the platform.": "Последний запуск поставщика, зарегистрированный платформой.",
    "Received": "Получено",
    "Created": "Создано",
    "Updated": "Обновлено",
    "Run a focused import when demonstrating the API layer to avoid unnecessary provider load.": "Запускайте точечный импорт при демонстрации API-слоя, чтобы не создавать лишнюю нагрузку на поставщика.",
    "After every run, check received, created and updated records before opening reports.": "После каждого запуска проверьте полученные, созданные и обновлённые записи перед открытием отчётов.",
    "Failed runs remain visible in the log so provider errors can be explained and traced.": "Неудачные запуски остаются в журнале, чтобы ошибки поставщика можно было объяснить и отследить.",
    "Synchronization trace": "След синхронизации",
    "Provider execution history, ingestion volume and technical messages.": "История запусков поставщика, объём загрузки и технические сообщения.",
    "No synchronization logs available.": "Журналы синхронизации отсутствуют.",
    "Failed run — %(provider)s / %(sync_type)s on %(started)s.": "Неудачный запуск — %(provider)s / %(sync_type)s от %(started)s.",

    # Analytics
    "Operational Intelligence": "Операционная аналитика",
    "Performance, routes, reports and source quality": "Производительность, маршруты, отчёты и качество источников",
    "Critical Supervision": "Критический контроль",
    "Elevated Supervision": "Усиленный контроль",
    "Stable Operations": "Стабильные операции",
    "Current flight performance overview": "Обзор текущей эффективности рейсов",
    "Disruption pressure is visible. Prioritize cancelled flights, delayed operations, and the busiest corridor before expanding the analysis.": "Наблюдается давление сбоев. Сначала проверьте отменённые рейсы, задержанные операции и самый загруженный коридор, затем расширяйте анализ.",
    "Operations remain readable, but active disruption pockets require targeted attention.": "Операционная картина остаётся читаемой, но отдельные зоны сбоев требуют целевого внимания.",
    "The visible operational picture is stable. Continue standard supervision and data validation.": "Видимая операционная картина стабильна. Продолжайте стандартный контроль и проверку данных.",
    "%(rate)s%% of records are currently in active flow.": "%(rate)s%% записей сейчас находятся в активном потоке.",
    "%(rate)s%% of the current dataset.": "%(rate)s%% текущего набора данных.",
    "%(rate)s%% active flow.": "%(rate)s%% активного потока.",
    "%(rate)s%% active share": "%(rate)s%% активной доли",
    "%(rate)s%% of the current flight dataset.": "%(rate)s%% текущего набора данных рейсов.",
    "%(rate)s%% delay rate.": "%(rate)s%% уровень задержек.",
    "%(rate)s%% cancellation rate.": "%(rate)s%% уровень отмен.",
    "%(rate)s%% of total records.": "%(rate)s%% от общего количества записей.",
    "Priority corridor to watch: %(route)s.": "Приоритетный коридор для контроля: %(route)s.",
    "Review cancelled flights and validate recovery actions before presenting the report.": "Проверьте отменённые рейсы и подтвердите действия восстановления перед представлением отчёта.",
    "Track delayed flights and compare them with route concentration and airport activity.": "Отслеживайте задержанные рейсы и сопоставляйте их с концентрацией маршрутов и активностью аэропортов.",
    "External synchronized data is dominant. Confirm API consistency and explain this as a hybrid data model.": "Внешние синхронизированные данные преобладают. Подтвердите согласованность API и объясните это как гибридную модель данных.",
    "No flight records are visible in this report. Check filters or synchronize operational data.": "В этом отчёте нет видимых записей о рейсах. Проверьте фильтры или синхронизируйте операционные данные.",

    # Map
    "All traffic": "Весь трафик",
    "Traffic Surface": "Карта трафика",
    "Live map view of operational traffic and exposed services.": "Картографический вид операционного трафика и отображаемых служб.",
    "Confirmed": "Подтверждено",
    "Associated": "Связано",
    "Low": "Низкий",
    "Simulated": "Смоделировано",
    "Selected flight": "Выбранный рейс",
    "Standby": "Ожидание",
    "Ready for inspection": "Готово к проверке",
    "Operational visibility": "Операционная видимость",
    "Clear reading": "Понятное чтение",
    "Use the map to identify active services, delayed traffic and flights that deserve closer attention.": "Используйте карту, чтобы определить активные службы, задержанный трафик и рейсы, требующие более пристального внимания.",
    "The panel keeps only the information needed for a fast operational review.": "Панель содержит только информацию, необходимую для быстрой операционной проверки.",
    "Start with a delayed flight, a selected route, or a service flagged in the visible traffic.": "Начните с задержанного рейса, выбранного маршрута или службы, отмеченной в видимом трафике.",
    "CRISIS": "КРИЗИС",
    "%(cancelled)s cancelled · %(delayed)s delayed · %(high_risk)s high risk.": "%(cancelled)s отменено · %(delayed)s задержано · %(high_risk)s высокий риск.",
}


FORMAT_RE = re.compile(
    r"%\((?P<name>[^)]+)\)"
    r"(?P<flags>[-+0 #]*)"
    r"(?P<width>\d+)?"
    r"(?P<precision>\.\d+)?"
    r"(?P<type>[diouxXeEfFgGcrs])"
)


def normalize(text):
    return " ".join((text or "").split())


def placeholders(text):
    return {match.group("name") for match in FORMAT_RE.finditer(text or "")}


def shaped_translation(source, translation):
    source = source or ""
    translation = translation or ""

    starts_newline = source.startswith("\n")
    ends_newline = source.endswith("\n")

    result = translation.strip()

    if starts_newline:
        result = "\n" + result

    if ends_newline:
        result = result + "\n"

    return result


def set_translation(entry, translation):
    expected = placeholders(entry.msgid)
    actual = placeholders(translation)

    if expected != actual:
        print("SKIPPED placeholder mismatch:")
        print(f"  msgid: {normalize(entry.msgid)}")
        print(f"  msgstr wanted: {translation}")
        print(f"  expected: {sorted(expected)}")
        print(f"  actual: {sorted(actual)}")
        return False

    entry.msgstr = shaped_translation(entry.msgid, translation)

    if "fuzzy" in entry.flags:
        entry.flags.remove("fuzzy")

    return True


def patch_po(path, translations, language_name):
    if not path.exists():
        print(f"{language_name}: missing {path}")
        return

    po = polib.pofile(str(path))
    normalized_map = {}

    for entry in po:
        if entry.obsolete or entry.msgid_plural:
            continue

        normalized_map.setdefault(normalize(entry.msgid), entry)

    updated = 0
    created = 0

    for source, translation in translations.items():
        normalized_source = normalize(source)
        entry = normalized_map.get(normalized_source)

        if entry:
            if set_translation(entry, translation):
                updated += 1
            continue

        if placeholders(source) != placeholders(translation):
            print("SKIPPED create placeholder mismatch:")
            print(f"  source: {source}")
            print(f"  translation: {translation}")
            continue

        new_entry = polib.POEntry(
            msgid=source,
            msgstr=translation,
        )
        po.append(new_entry)
        normalized_map[normalized_source] = new_entry
        created += 1

    po.save(str(path))
    print(f"{language_name}: updated={updated}, created={created}, file={path}")


def main():
    patch_po(PO_FILES["fr"], FR, "French")
    patch_po(PO_FILES["ru"], RU, "Russian")


if __name__ == "__main__":
    main()