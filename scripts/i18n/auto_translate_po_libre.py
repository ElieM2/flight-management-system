from pathlib import Path
import html
import os
import re
import time

import polib
import requests


BASE_DIR = Path(__file__).resolve().parent.parent

LIBRETRANSLATE_URL = os.environ.get(
    "LIBRETRANSLATE_URL",
    "http://127.0.0.1:5000",
).rstrip("/")

PO_FILES = {
    "fr": BASE_DIR / "locale" / "fr" / "LC_MESSAGES" / "django.po",
    "ru": BASE_DIR / "locale" / "ru" / "LC_MESSAGES" / "django.po",
}

TARGET_LANGS = {
    "fr": "fr",
    "ru": "ru",
}

LANGUAGE_NAMES = {
    "fr": "French",
    "ru": "Russian",
}

REQUEST_TIMEOUT = 120
REQUEST_DELAY = 0.35
MAX_ITEMS_PER_RUN = 700

PLACEHOLDER_RE = re.compile(
    r"%\((?P<name>[^)]+)\)"
    r"(?P<flags>[-+0 #]*)"
    r"(?P<width>\d+)?"
    r"(?P<precision>\.\d+)?"
    r"(?P<type>[diouxXeEfFgGcrs])"
)

BRACE_PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")
DJANGO_TAG_RE = re.compile(r"\{[%#].*?[%#]\}", re.DOTALL)
DJANGO_VARIABLE_RE = re.compile(r"\{\{.*?\}\}", re.DOTALL)

TECH_TERMS = [
    "FlightLogos",
    "AirMonitor",
    "Aviationstack",
    "aviationstack",
    "OpenSky",
    "AirLabs",
    "API",
    "KPI",
    "IATA",
    "ICAO",
    "CDG",
    "BCN",
    "OPS",
    "Dashboard",
    "Copilot",
    "Flight",
    "Flights",
    "Provider",
    "Providers",
    "Run",
    "Runs",
    "Status",
    "Monitoring",
    "Operational",
    "Live",
    "Map",
    "Data",
]


def normalize(text):
    return " ".join((text or "").split())


def has_text(value):
    return bool((value or "").strip())


def is_probably_not_ui_text(text):
    clean = (text or "").strip()

    if not clean:
        return True

    if clean.startswith("http://") or clean.startswith("https://"):
        return True

    if clean.startswith("/") and " " not in clean:
        return True

    if clean.lower().endswith((".png", ".jpg", ".jpeg", ".svg", ".webp", ".css", ".js")):
        return True

    if clean in ["api", "local", "iata", "icao"]:
        return True

    if re.fullmatch(r"[A-Z0-9_\-./:]+", clean) and len(clean) <= 30:
        return True

    return False


def placeholders(text):
    found = set()

    for match in PLACEHOLDER_RE.finditer(text or ""):
        found.add(match.group(0))

    for match in BRACE_PLACEHOLDER_RE.finditer(text or ""):
        found.add(match.group(0))

    for match in DJANGO_TAG_RE.finditer(text or ""):
        found.add(match.group(0))

    for match in DJANGO_VARIABLE_RE.finditer(text or ""):
        found.add(match.group(0))

    return found


def protect_text(text):
    protected = text or ""
    token_map = {}

    protected_items = []

    for item in sorted(placeholders(protected), key=len, reverse=True):
        protected_items.append(item)

    for term in sorted(TECH_TERMS, key=len, reverse=True):
        if term in protected:
            protected_items.append(term)

    seen = set()
    clean_items = []

    for item in protected_items:
        if item not in seen:
            clean_items.append(item)
            seen.add(item)

    for index, item in enumerate(clean_items):
        token = f"ZXPROTECT{index}ZX"
        protected = protected.replace(item, token)
        token_map[token] = item

    return protected, token_map


def restore_text(text, token_map):
    restored = text or ""

    for token, original in token_map.items():
        restored = restored.replace(token, original)

    return restored


def preserve_newlines(source, translation):
    source = source or ""
    translation = translation or ""

    result = translation.strip()

    if source.startswith("\n") and not result.startswith("\n"):
        result = "\n" + result

    if source.endswith("\n") and not result.endswith("\n"):
        result = result + "\n"

    return result


def validate_placeholders(source, translation):
    return placeholders(source) == placeholders(translation)


def libretranslate_is_ready():
    try:
        response = requests.get(
            f"{LIBRETRANSLATE_URL}/languages",
            timeout=REQUEST_TIMEOUT,
        )
        return response.status_code == 200
    except requests.RequestException:
        return False


def translate_text(source, target_lang):
    if is_probably_not_ui_text(source):
        return source

    protected_source, token_map = protect_text(source)

    payload = {
        "q": protected_source,
        "source": "en",
        "target": target_lang,
        "format": "text",
    }

    response = requests.post(
        f"{LIBRETRANSLATE_URL}/translate",
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"LibreTranslate error {response.status_code}: {response.text}"
        )

    data = response.json()
    translated = data.get("translatedText", "")

    translated = html.unescape(translated)
    translated = restore_text(translated, token_map)
    translated = preserve_newlines(source, translated)

    if not validate_placeholders(source, translated):
        print("-" * 80)
        print("Skipped because placeholders changed")
        print(f"Source:      {normalize(source)}")
        print(f"Translation: {normalize(translated)}")
        print(f"Expected:    {sorted(placeholders(source))}")
        print(f"Actual:      {sorted(placeholders(translated))}")
        return ""

    return translated


def get_plural_value(entry, key):
    return entry.msgstr_plural.get(key, "") or entry.msgstr_plural.get(str(key), "")


def set_plural_value(entry, key, value):
    existing = dict(entry.msgstr_plural)

    normalized = {}

    for existing_key, existing_value in existing.items():
        try:
            normalized[int(existing_key)] = existing_value
        except (TypeError, ValueError):
            normalized[existing_key] = existing_value

    normalized[int(key)] = value
    entry.msgstr_plural = normalized


def normalize_plural_keys(po):
    for entry in po:
        if not entry.msgid_plural:
            continue

        if not entry.msgstr_plural:
            continue

        normalized = {}

        for key, value in dict(entry.msgstr_plural).items():
            try:
                normalized[int(key)] = value
            except (TypeError, ValueError):
                normalized[key] = value

        entry.msgstr_plural = normalized


def collect_entries(po):
    items = []

    for entry in po:
        if entry.obsolete:
            continue

        if entry.msgid_plural:
            current_zero = get_plural_value(entry, 0)
            current_one = get_plural_value(entry, 1)

            if not has_text(current_zero):
                items.append(("plural", entry, 0, entry.msgid))

            if not has_text(current_one):
                items.append(("plural", entry, 1, entry.msgid_plural))

            continue

        if not has_text(entry.msgstr):
            items.append(("singular", entry, None, entry.msgid))

    return items


def fill_po_file(language_code):
    path = PO_FILES[language_code]
    target_lang = TARGET_LANGS[language_code]
    language_name = LANGUAGE_NAMES[language_code]

    if not path.exists():
        print(f"{language_name}: file not found: {path}")
        return

    po = polib.pofile(str(path))
    normalize_plural_keys(po)

    entries = collect_entries(po)

    if not entries:
        po.save(str(path))
        print(f"{language_name}: nothing to translate.")
        return

    print(f"{language_name}: {len(entries)} empty item(s) found.")

    translated_count = 0
    skipped_count = 0
    error_count = 0

    limit = min(len(entries), MAX_ITEMS_PER_RUN)

    for index, item in enumerate(entries[:limit], start=1):
        kind, entry, plural_key, source = item

        print(f"{language_name}: {index}/{limit} → {normalize(source)[:100]}")

        try:
            translated = translate_text(source, target_lang)
        except Exception as exc:
            error_count += 1
            print(f"ERROR: {exc}")
            time.sleep(REQUEST_DELAY)
            continue

        if not has_text(translated):
            skipped_count += 1
            time.sleep(REQUEST_DELAY)
            continue

        if kind == "singular":
            entry.msgstr = translated
        else:
            set_plural_value(entry, plural_key, translated)

        if "fuzzy" in entry.flags:
            entry.flags.remove("fuzzy")

        translated_count += 1

        if translated_count % 20 == 0:
            normalize_plural_keys(po)
            po.save(str(path))

        time.sleep(REQUEST_DELAY)

    normalize_plural_keys(po)
    po.save(str(path))

    print(
        f"{language_name}: translated={translated_count}, "
        f"skipped={skipped_count}, errors={error_count}, file={path}"
    )


def main():
    print(f"LibreTranslate URL: {LIBRETRANSLATE_URL}")

    if not libretranslate_is_ready():
        raise RuntimeError(
            "LibreTranslate is not ready. Open http://127.0.0.1:5000 "
            "and make sure the server is running."
        )

    fill_po_file("fr")
    fill_po_file("ru")


if __name__ == "__main__":
    main()