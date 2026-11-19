from pathlib import Path
import os
import re
import time
import html
import requests
import polib


BASE_DIR = Path(__file__).resolve().parent.parent

PO_FILES = {
    "fr": BASE_DIR / "locale" / "fr" / "LC_MESSAGES" / "django.po",
    "ru": BASE_DIR / "locale" / "ru" / "LC_MESSAGES" / "django.po",
}

TARGET_LANGS = {
    "fr": "FR",
    "ru": "RU",
}

DEEPL_API_KEY = os.environ.get("DEEPL_API_KEY", "").strip()

DEEPL_FREE_ENDPOINT = "https://api-free.deepl.com/v2/translate"
DEEPL_PRO_ENDPOINT = "https://api.deepl.com/v2/translate"

# Change to True only if your key is a DeepL Pro key.
USE_DEEPL_PRO = False

DEEPL_ENDPOINT = DEEPL_PRO_ENDPOINT if USE_DEEPL_PRO else DEEPL_FREE_ENDPOINT


PLACEHOLDER_RE = re.compile(
    r"%\((?P<name>[^)]+)\)"
    r"(?P<flags>[-+0 #]*)"
    r"(?P<width>\d+)?"
    r"(?P<precision>\.\d+)?"
    r"(?P<type>[diouxXeEfFgGcrs])"
)

BRACE_PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")

TECH_TERMS = [
    "FlightLogos",
    "API",
    "KPI",
    "IATA",
    "ICAO",
    "CDG",
    "BCN",
    "OPS",
    "Dashboard",
    "Copilot",
    "Aviationstack",
    "OpenSky",
    "AirLabs",
]


def normalize(text):
    return " ".join((text or "").split())


def has_text(value):
    return bool((value or "").strip())


def placeholders(text):
    names = set()

    for match in PLACEHOLDER_RE.finditer(text or ""):
        names.add(match.group(0))

    for match in BRACE_PLACEHOLDER_RE.finditer(text or ""):
        names.add(match.group(0))

    return names


def protect_text(text):
    """
    Replace dangerous variables/technical terms with safe tokens before translation.
    """
    protected = text
    tokens = {}

    all_items = []

    for item in sorted(placeholders(text), key=len, reverse=True):
        all_items.append(item)

    for term in TECH_TERMS:
        if term in protected:
            all_items.append(term)

    for index, item in enumerate(all_items):
        token = f"ZXPROTECT{index}ZX"
        protected = protected.replace(item, token)
        tokens[token] = item

    return protected, tokens


def restore_text(text, tokens):
    restored = text

    for token, original in tokens.items():
        restored = restored.replace(token, original)

    return restored


def shaped_translation(source, translation):
    """
    Preserve leading/trailing newlines from the msgid.
    """
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


def validate_translation(source, translation):
    source_placeholders = placeholders(source)
    translated_placeholders = placeholders(translation)

    return source_placeholders == translated_placeholders


def translate_batch(texts, target_lang):
    if not DEEPL_API_KEY:
        raise RuntimeError(
            "DEEPL_API_KEY is missing. Set it first with: "
            '$env:DEEPL_API_KEY="YOUR_KEY"'
        )

    if not texts:
        return []

    protected_texts = []
    token_maps = []

    for text in texts:
        protected, tokens = protect_text(text)
        protected_texts.append(protected)
        token_maps.append(tokens)

    payload = {
        "auth_key": DEEPL_API_KEY,
        "target_lang": target_lang,
        "source_lang": "EN",
        "tag_handling": "html",
        "preserve_formatting": "1",
        "text": protected_texts,
    }

    response = requests.post(DEEPL_ENDPOINT, data=payload, timeout=60)

    if response.status_code != 200:
        raise RuntimeError(
            f"DeepL request failed: {response.status_code} - {response.text}"
        )

    data = response.json()
    translated_items = data.get("translations", [])

    if len(translated_items) != len(texts):
        raise RuntimeError(
            f"DeepL returned {len(translated_items)} translations for {len(texts)} texts."
        )

    results = []

    for index, item in enumerate(translated_items):
        translated = item.get("text", "")
        translated = html.unescape(translated)
        translated = restore_text(translated, token_maps[index])
        translated = shaped_translation(texts[index], translated)

        if not validate_translation(texts[index], translated):
            print("SKIPPED placeholder mismatch after translation")
            print(f"  source:      {normalize(texts[index])}")
            print(f"  translation: {normalize(translated)}")
            print(f"  source vars: {sorted(placeholders(texts[index]))}")
            print(f"  trans vars:  {sorted(placeholders(translated))}")
            results.append("")
        else:
            results.append(translated)

    return results


def collect_entries(po):
    entries = []

    for entry in po:
        if entry.obsolete:
            continue

        if entry.msgid_plural:
            # Plural entries are handled carefully.
            # Translate singular and plural separately only when empty.
            for key, source in [
                ("0", entry.msgid),
                ("1", entry.msgid_plural),
            ]:
                current = entry.msgstr_plural.get(key, "")
                if not has_text(current):
                    entries.append(("plural", entry, key, source))
            continue

        if not has_text(entry.msgstr):
            entries.append(("singular", entry, None, entry.msgid))

    return entries


def auto_translate_file(path, target_lang, language_name, batch_size=20):
    if not path.exists():
        print(f"{language_name}: missing file {path}")
        return

    po = polib.pofile(str(path))
    entries = collect_entries(po)

    if not entries:
        print(f"{language_name}: nothing to translate.")
        return

    print(f"{language_name}: {len(entries)} empty translation item(s) found.")

    translated_count = 0
    skipped_count = 0

    for start in range(0, len(entries), batch_size):
        chunk = entries[start:start + batch_size]
        sources = [item[3] for item in chunk]

        print(
            f"{language_name}: translating {start + 1} - "
            f"{min(start + batch_size, len(entries))} / {len(entries)}"
        )

        translations = translate_batch(sources, target_lang)

        for item, translated in zip(chunk, translations):
            kind, entry, plural_key, source = item

            if not has_text(translated):
                skipped_count += 1
                continue

            if kind == "singular":
                entry.msgstr = translated
            else:
                entry.msgstr_plural[plural_key] = translated

            if "fuzzy" in entry.flags:
                entry.flags.remove("fuzzy")

            translated_count += 1

        po.save(str(path))
        time.sleep(0.5)

    po.save(str(path))

    print(
        f"{language_name}: translated={translated_count}, "
        f"skipped={skipped_count}, file={path}"
    )


def main():
    auto_translate_file(PO_FILES["fr"], TARGET_LANGS["fr"], "French")
    auto_translate_file(PO_FILES["ru"], TARGET_LANGS["ru"], "Russian")


if __name__ == "__main__":
    main()