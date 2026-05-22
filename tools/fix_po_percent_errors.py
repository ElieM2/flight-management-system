from pathlib import Path
import re
import polib


BASE_DIR = Path(__file__).resolve().parent.parent

PO_FILES = [
    BASE_DIR / "locale" / "fr" / "LC_MESSAGES" / "django.po",
    BASE_DIR / "locale" / "ru" / "LC_MESSAGES" / "django.po",
]


PLACEHOLDER_PATTERN = re.compile(
    r"%\([^)]+\)[#0\- +]?(?:\d+|\*)?(?:\.\d+)?[diouxXeEfFgGcrs]"
)


def extract_placeholders(text):
    if not text:
        return []

    return PLACEHOLDER_PATTERN.findall(text)


def normalize_msgstr(entry):
    """
    If msgstr does not contain all placeholders from msgid,
    the safest correction is to copy msgid into msgstr.

    It is better to show English text than to break Django compilation.
    """
    source_placeholders = extract_placeholders(entry.msgid)
    target_placeholders = extract_placeholders(entry.msgstr)

    if not source_placeholders:
        return False

    missing = [item for item in source_placeholders if item not in target_placeholders]

    if missing:
        entry.msgstr = entry.msgid
        return True

    return False


def normalize_plural(entry):
    changed = False

    if not entry.msgid_plural:
        return changed

    singular_placeholders = extract_placeholders(entry.msgid)
    plural_placeholders = extract_placeholders(entry.msgid_plural)

    for key, value in list(entry.msgstr_plural.items()):
        current_placeholders = extract_placeholders(value)

        required_placeholders = plural_placeholders if key != "0" else singular_placeholders

        missing = [
            item for item in required_placeholders
            if item not in current_placeholders
        ]

        if missing:
            if key == "0":
                entry.msgstr_plural[key] = entry.msgid
            else:
                entry.msgstr_plural[key] = entry.msgid_plural
            changed = True

    return changed


def clean_file(path):
    po = polib.pofile(str(path))
    fixed = 0

    for entry in po:
        if entry.obsolete:
            continue

        if normalize_msgstr(entry):
            fixed += 1

        if normalize_plural(entry):
            fixed += 1

    po.save(str(path))

    print(f"{path}: fixed {fixed} percent placeholder issue(s)")


def main():
    for path in PO_FILES:
        if not path.exists():
            print(f"Missing file: {path}")
            continue

        clean_file(path)


if __name__ == "__main__":
    main()