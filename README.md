# Flight Management System

Application web de suivi et de gestion des opérations aériennes. Elle présente un catalogue public (vols, aéroports, compagnies, appareils), un tableau de bord après connexion, un module de surveillance (dont une carte), des pages d’analyse opérationnelle, et des imports depuis des sources externes. Un module **assistant** (`apps/copilot`) permet d’interroger les données déjà enregistrées dans l’application ; les connecteurs optionnels vers des services externes sont désactivés par défaut.

## Stack

- Python 3.12 à 3.15
- Django 6 et Django REST Framework
- SQLite par défaut (`db.sqlite3`)
- `python-dotenv` pour le fichier `.env` à la racine du projet

## Installation

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # sous Unix : cp .env.example .env
```

Dans `.env`, définissez au minimum un `SECRET_KEY` Django. Les autres clés peuvent rester vides pour un usage local.

```bash
python manage.py migrate
python manage.py seed_demo_operations
python manage.py createsuperuser
python manage.py runserver
```

L’interface publique est alors disponible à l’adresse du serveur de développement (par défaut http://127.0.0.1:8000/). Le tableau de bord, la surveillance, la carte, les analyses et l’assistant nécessitent une connexion.

## Clés API optionnelles

Elles sont toutes facultatives. Sans elles, le catalogue local et les données de démonstration fonctionnent normalement.

- `AVIATIONSTACK_API_KEY` — import de vols (`sync_aviationstack`, `auto_sync_aviationstack`)
- `AIRLABS_API_KEY` — enrichissement des aéroports (`enrich_airports`)
- Météo carte : radar RainViewer et observations Open-Meteo (aucune clé requise)
- `OPENSKY_CLIENT_ID` / `OPENSKY_CLIENT_SECRET` — trafic live OpenSky (`sync_opensky`)
- `DEEPL_API_KEY` — scripts de traduction hors application (`scripts/i18n/`)
- `OPENAI_API_KEY` — uniquement si l’assistant est configuré pour un prestataire externe

Les paramètres `COPILOT_*` du fichier d’exemple laissent l’assistant en mode local, sans appel externe.

Commandes locales utiles, sans clé API : `fill_airline_country_codes`, `fill_airport_coordinates`, `assign_missing_aircraft`, `backfill_flight_history`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

`requirements-dev.txt` installe notamment pytest et pytest-django, en plus des dépendances de l’application.

## Déploiement sur Render

Le fichier `render.yaml` décrit un service web gratuit. Le dépôt ne doit pas contenir de fichier `.env` ni de secrets.

Sur Render, renseignez au minimum :

- `DEMO_USERNAME` et `DEMO_PASSWORD` — compte de démonstration en lecture seule (pas administrateur)
- éventuellement les clés API déjà documentées plus haut, si vous voulez les imports live

`SECRET_KEY` est généré par Render. `DEBUG` est fixé à `0`. L’hôte public (`RENDER_EXTERNAL_HOSTNAME`) est ajouté automatiquement à `ALLOWED_HOSTS` et `CSRF_TRUSTED_ORIGINS`.

À chaque déploiement, `build.sh` installe les dépendances, lance `collectstatic`, applique les migrations, puis régénère les données de démonstration (`seed_demo_operations`) et le compte de démo (`ensure_demo_user`). Le disque du plan gratuit est éphémère : la base SQLite est donc réinitialisée à partir des données de démo à chaque build.

Le compte de démo peut se connecter et consulter le tableau de bord, la surveillance, la carte et les analyses. Il ne peut pas modifier le profil ni lancer une synchronisation. Après une période d’inactivité, le service gratuit se met en veille ; le premier chargement peut prendre environ une minute.
